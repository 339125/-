from typing import List, Dict, Any
import pandas as pd
import numpy as np
from ..data.models import Trade, Order
from ..utils.logger import logger

class PerformanceAnalyzer:
    def __init__(self, trades: List[Trade], orders: List[Order], equity_curve: List[Dict[str, Any]]):
        self.trades = trades
        self.orders = orders
        self.equity_curve = equity_curve

    def calculate_metrics(self) -> Dict[str, Any]:
        if not self.equity_curve or len(self.equity_curve) < 2:
            return {}

        equity_values = [e['equity'] for e in self.equity_curve]
        returns = self._calculate_returns(equity_values)

        metrics = {
            'total_return': self._total_return(equity_values),
            'annualized_return': self._annualized_return(returns),
            'volatility': self._volatility(returns),
            'sharpe_ratio': self._sharpe_ratio(returns),
            'sortino_ratio': self._sortino_ratio(returns),
            'max_drawdown': self._max_drawdown(equity_values),
            'calmar_ratio': self._calmar_ratio(equity_values, returns),
            'win_rate': self._win_rate(),
            'profit_factor': self._profit_factor(),
            'avg_trade': self._avg_trade(),
            'avg_winning_trade': self._avg_winning_trade(),
            'avg_losing_trade': self._avg_losing_trade(),
            'largest_win': self._largest_win(),
            'largest_loss': self._largest_loss(),
            'total_trades': len(self.orders),
            'winning_trades': self._winning_trades_count(),
            'losing_trades': self._losing_trades_count()
        }

        return metrics

    def _calculate_returns(self, equity_values: List[float]) -> List[float]:
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i-1] > 0:
                ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                returns.append(ret)
        return returns

    def _total_return(self, equity_values: List[float]) -> float:
        if not equity_values or equity_values[0] == 0:
            return 0.0
        return ((equity_values[-1] - equity_values[0]) / equity_values[0]) * 100

    def _annualized_return(self, returns: List[float]) -> float:
        if not returns:
            return 0.0
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        if volatility == 0:
            return 0.0
        return (avg_return + 1) ** 252 - 1

    def _volatility(self, returns: List[float]) -> float:
        if not returns:
            return 0.0
        return np.std(returns) * np.sqrt(252) * 100

    def _sharpe_ratio(self, returns: List[float]) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        if std_return == 0:
            return 0.0
        return (avg_return / std_return) * np.sqrt(252)

    def _sortino_ratio(self, returns: List[float]) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = np.mean(returns)
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return 0.0
        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0.0
        return (avg_return / downside_std) * np.sqrt(252)

    def _max_drawdown(self, equity_values: List[float]) -> float:
        if not equity_values:
            return 0.0
        running_max = np.maximum.accumulate(equity_values)
        drawdowns = (equity_values - running_max) / running_max
        return abs(np.min(drawdowns)) * 100

    def _calmar_ratio(self, equity_values: List[float], returns: List[float]) -> float:
        max_dd = self._max_drawdown(equity_values)
        if max_dd == 0:
            return 0.0
        ann_return = self._annualized_return(returns)
        return ann_return / max_dd

    def _win_rate(self) -> float:
        winning = self._winning_trades_count()
        total = len(self.orders)
        if total == 0:
            return 0.0
        return (winning / total) * 100

    def _winning_trades_count(self) -> int:
        sell_trades = [t for t in self.trades if t.side.upper() == 'SELL']
        return sum(1 for t in sell_trades if self._trade_pnl(t) > 0)

    def _losing_trades_count(self) -> int:
        sell_trades = [t for t in self.trades if t.side.upper() == 'SELL']
        return sum(1 for t in sell_trades if self._trade_pnl(t) < 0)

    def _profit_factor(self) -> float:
        gross_profit = 0.0
        gross_loss = 0.0
        for trade in self.trades:
            pnl = self._trade_pnl(trade)
            if pnl > 0:
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)
        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float('inf')
        return gross_profit / gross_loss

    def _avg_trade(self) -> float:
        if not self.trades:
            return 0.0
        pnls = [self._trade_pnl(t) for t in self.trades]
        return np.mean(pnls)

    def _avg_winning_trade(self) -> float:
        winning_pnls = [self._trade_pnl(t) for t in self.trades 
                       if self._trade_pnl(t) > 0]
        return np.mean(winning_pnls) if winning_pnls else 0.0

    def _avg_losing_trade(self) -> float:
        losing_pnls = [self._trade_pnl(t) for t in self.trades 
                      if self._trade_pnl(t) < 0]
        return np.mean(losing_pnls) if losing_pnls else 0.0

    def _largest_win(self) -> float:
        pnls = [self._trade_pnl(t) for t in self.trades]
        return max(pnls) if pnls else 0.0

    def _largest_loss(self) -> float:
        pnls = [self._trade_pnl(t) for t in self.trades]
        return min(pnls) if pnls else 0.0

    def _trade_pnl(self, trade: Trade) -> float:
        return trade.quantity * (trade.price - trade.price) 

    def generate_report(self) -> str:
        metrics = self.calculate_metrics()
        if not metrics:
            return "No data available for analysis"

        report = "\n" + "="*60 + "\n"
        report += "Performance Analysis Report\n"
        report += "="*60 + "\n\n"

        report += "Returns & Risk Metrics:\n"
        report += "-"*40 + "\n"
        report += f"Total Return:         {metrics.get('total_return', 0):.2f}%\n"
        report += f"Annualized Return:    {metrics.get('annualized_return', 0):.2f}%\n"
        report += f"Volatility:           {metrics.get('volatility', 0):.2f}%\n"
        report += f"Sharpe Ratio:         {metrics.get('sharpe_ratio', 0):.2f}\n"
        report += f"Sortino Ratio:        {metrics.get('sortino_ratio', 0):.2f}\n"
        report += f"Max Drawdown:         {metrics.get('max_drawdown', 0):.2f}%\n"
        report += f"Calmar Ratio:         {metrics.get('calmar_ratio', 0):.2f}\n\n"

        report += "Trading Statistics:\n"
        report += "-"*40 + "\n"
        report += f"Total Trades:         {metrics.get('total_trades', 0)}\n"
        report += f"Winning Trades:       {metrics.get('winning_trades', 0)}\n"
        report += f"Losing Trades:        {metrics.get('losing_trades', 0)}\n"
        report += f"Win Rate:            {metrics.get('win_rate', 0):.2f}%\n"
        report += f"Profit Factor:       {metrics.get('profit_factor', 0):.2f}\n\n"

        report += "Trade Analysis:\n"
        report += "-"*40 + "\n"
        report += f"Average Trade:       ${metrics.get('avg_trade', 0):.2f}\n"
        report += f"Avg Winning Trade:   ${metrics.get('avg_winning_trade', 0):.2f}\n"
        report += f"Avg Losing Trade:    ${metrics.get('avg_losing_trade', 0):.2f}\n"
        report += f"Largest Win:         ${metrics.get('largest_win', 0):.2f}\n"
        report += f"Largest Loss:        ${metrics.get('largest_loss', 0):.2f}\n"

        report += "\n" + "="*60 + "\n"
        return report

    def to_dataframe(self) -> pd.DataFrame:
        if not self.equity_curve:
            return pd.DataFrame()
        return pd.DataFrame(self.equity_curve)
