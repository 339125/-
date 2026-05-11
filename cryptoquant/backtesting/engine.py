from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from ..data.models import Candlestick, Order, Position, Signal, Trade, Portfolio
from ..exchange_adapters.base import BaseExchangeAdapter
from ..utils.logger import logger

@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    maker_fee: float = 0.001
    taker_fee: float = 0.001

class OrderSimulator:
    def __init__(self, slippage: float = 0.0005, commission: float = 0.001):
        self.slippage = slippage
        self.commission = commission

    def execute_market_order(self, side: str, quantity: float, 
                           current_price: float) -> Dict[str, Any]:
        if side.upper() == 'BUY':
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)

        commission_fee = quantity * execution_price * self.commission

        return {
            'execution_price': execution_price,
            'commission': commission_fee,
            'total_cost': quantity * execution_price + commission_fee,
            'filled': True
        }

    def execute_limit_order(self, side: str, quantity: float,
                          limit_price: float, current_price: float) -> Dict[str, Any]:
        if side.upper() == 'BUY' and current_price <= limit_price:
            execution_price = limit_price
            filled = True
        elif side.upper() == 'SELL' and current_price >= limit_price:
            execution_price = limit_price
            filled = True
        else:
            return {'filled': False}

        commission_fee = quantity * execution_price * self.commission

        return {
            'execution_price': execution_price,
            'commission': commission_fee,
            'total_cost': quantity * execution_price + commission_fee,
            'filled': filled
        }

class BacktestEngine:
    def __init__(self, exchange_adapter: Optional[BaseExchangeAdapter] = None,
                 config: Optional[BacktestConfig] = None):
        self.exchange = exchange_adapter
        self.config = config or BacktestConfig()
        self.order_simulator = OrderSimulator(
            self.config.slippage,
            self.config.commission
        )
        self.portfolio = None
        self.orders = []
        self.trades = []
        self.equity_curve = []

    def initialize(self, initial_capital: Optional[float] = None):
        capital = initial_capital or self.config.initial_capital
        self.portfolio = Portfolio(
            initial_capital=capital,
            current_capital=capital,
            positions={},
            trades=[],
            equity_curve=[]
        )
        self.orders = []
        self.trades = []
        self.equity_curve = []

    def run(self, strategy, symbol: str, start_date: str, 
            end_date: str, interval: str = '1h',
            data: Optional[pd.DataFrame] = None) -> 'BacktestResults':
        from ..data.fetcher import MarketDataFetcher

        if not self.portfolio:
            self.initialize()

        logger.info(f"Starting backtest: {symbol} from {start_date} to {end_date}")

        if data is None:
            fetcher = MarketDataFetcher(self.exchange)
            df = fetcher.fetch_klines_dataframe(symbol, interval, start_date, end_date)
        else:
            df = data

        if df.empty:
            logger.error("No data fetched for backtest")
            return BacktestResults()

        strategy.on_init()

        prices = {}
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp() * 1000)
            prices[symbol] = row['close']

            self._update_positions(symbol, row['close'])
            self._update_equity(timestamp, prices)

            signal = strategy.on_data(df.loc[:idx], symbol)

            if signal:
                self._process_signal(signal, row['close'], timestamp)

        results = self._calculate_results()
        logger.info(f"Backtest completed: {results.total_trades} trades")
        return results

    def _process_signal(self, signal: Signal, current_price: float, timestamp: int):
        if signal.side.upper() not in ['BUY', 'SELL']:
            return

        quantity = signal.quantity or self._calculate_position_size(
            signal.side, signal.strength, current_price
        )

        if quantity <= 0:
            return

        execution = self.order_simulator.execute_market_order(
            signal.side, quantity, current_price
        )

        if not execution['filled']:
            return

        order = Order(
            order_id=f"bt_{timestamp}",
            symbol=signal.symbol,
            side=signal.side,
            order_type='MARKET',
            quantity=quantity,
            price=execution['execution_price'],
            status='FILLED',
            filled_quantity=quantity,
            average_price=execution['execution_price'],
            timestamp=timestamp,
            commission=execution['commission']
        )

        self.orders.append(order)
        self._apply_trade(order, current_price)

        trade = Trade(
            trade_id=f"trade_{len(self.trades)}",
            order_id=order.order_id,
            symbol=signal.symbol,
            side=signal.side,
            price=execution['execution_price'],
            quantity=quantity,
            commission=execution['commission'],
            timestamp=timestamp
        )
        self.trades.append(trade)

    def _apply_trade(self, order: Order, current_price: float):
        symbol = order.symbol

        if order.side.upper() == 'BUY':
            if symbol not in self.portfolio.positions:
                self.portfolio.positions[symbol] = Position(symbol=symbol)

            pos = self.portfolio.positions[symbol]
            cost = order.quantity * order.average_price + order.commission
            self.portfolio.current_capital -= cost
            pos.update_entry_price(order.quantity, order.average_price)

        elif order.side.upper() == 'SELL':
            if symbol in self.portfolio.positions:
                pos = self.portfolio.positions[symbol]
                proceeds = order.quantity * order.average_price - order.commission
                self.portfolio.current_capital += proceeds

                realized_pnl = (order.average_price - pos.average_entry_price) * order.quantity
                pos.realized_pnl += realized_pnl

                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    del self.portfolio.positions[symbol]

    def _update_positions(self, symbol: str, current_price: float):
        if symbol in self.portfolio.positions:
            pos = self.portfolio.positions[symbol]
            pos.unrealized_pnl = (current_price - pos.average_entry_price) * pos.quantity

    def _update_equity(self, timestamp: int, prices: Dict[str, float]):
        total_value = self.portfolio.get_total_value(prices)
        self.portfolio.equity_curve.append({
            'timestamp': timestamp,
            'equity': total_value,
            'capital': self.portfolio.current_capital
        })

    def _calculate_position_size(self, side: str, strength: float,
                                price: float) -> float:
        if side.upper() == 'SELL':
            if not self.portfolio.positions:
                return 0.0
            return self.portfolio.positions.get(list(self.portfolio.positions.keys())[0], 
                                                Position(symbol='')).quantity

        max_position_value = self.portfolio.initial_capital * 0.1 * strength
        quantity = max_position_value / price
        return round(quantity, 6)

    def _calculate_results(self) -> 'BacktestResults':
        if not self.equity_curve:
            self.equity_curve = self.portfolio.equity_curve

        if len(self.equity_curve) < 2:
            return BacktestResults()

        equity_values = [e['equity'] for e in self.equity_curve]
        initial = self.portfolio.initial_capital
        final = equity_values[-1]

        total_return = (final - initial) / initial * 100

        returns = np.diff(equity_values) / equity_values[:-1]
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

        sharpe_ratio = 0.0
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)

        running_max = np.maximum.accumulate(equity_values)
        drawdowns = (equity_values - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns)) * 100

        winning_trades = [t for t in self.trades if t.side.upper() == 'SELL']
        total_trades = len(self.orders)

        win_rate = 0.0
        if winning_trades:
            profitable = sum(1 for t in winning_trades 
                           if self._get_trade_pnl(t) > 0)
            win_rate = profitable / len(winning_trades) * 100

        return BacktestResults(
            initial_capital=initial,
            final_capital=final,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            win_rate=win_rate,
            equity_curve=self.equity_curve,
            orders=self.orders,
            trades=self.trades
        )

    def _get_trade_pnl(self, trade: Trade) -> float:
        symbol = trade.symbol
        if symbol in self.portfolio.positions:
            pos = self.portfolio.positions[symbol]
            return (trade.price - pos.average_entry_price) * trade.quantity
        return 0.0

    def get_current_positions(self) -> Dict[str, Position]:
        return self.portfolio.positions.copy()

    def get_open_orders(self) -> List[Order]:
        return [o for o in self.orders if o.status == 'NEW']

@dataclass
class BacktestResults:
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': f"{self.total_return:.2f}%",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'max_drawdown': f"{self.max_drawdown:.2f}%",
            'total_trades': self.total_trades,
            'win_rate': f"{self.win_rate:.2f}%"
        }

    def print_summary(self):
        print("\n" + "="*50)
        print("Backtest Results Summary")
        print("="*50)
        print(f"Initial Capital:    ${self.initial_capital:,.2f}")
        print(f"Final Capital:      ${self.final_capital:,.2f}")
        print(f"Total Return:       {self.total_return:.2f}%")
        print(f"Sharpe Ratio:       {self.sharpe_ratio:.2f}")
        print(f"Max Drawdown:       {self.max_drawdown:.2f}%")
        print(f"Total Trades:       {self.total_trades}")
        print(f"Win Rate:           {self.win_rate:.2f}%")
        print("="*50 + "\n")
