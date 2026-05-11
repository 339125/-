from typing import Dict, List, Any
from datetime import datetime
from ..data.models import Portfolio, Position, Order

class RiskController:
    def __init__(self, daily_loss_limit: float = 0.05,
                 max_positions: int = 5,
                 max_correlation: float = 0.7):
        self.daily_loss_limit = daily_loss_limit
        self.max_positions = max_positions
        self.max_correlation = max_correlation
        self.daily_pnl = 0.0
        self.daily_start_capital = 0.0
        self.blocked_symbols = set()

    def start_new_day(self, capital: float):
        self.daily_pnl = 0.0
        self.daily_start_capital = capital
        self.blocked_symbols.clear()

    def update_daily_pnl(self, pnl: float):
        self.daily_pnl += pnl

    def check_trading_allowed(self, symbol: str) -> tuple[bool, str]:
        if symbol in self.blocked_symbols:
            return False, f"Trading blocked for {symbol}"

        daily_return = abs(self.daily_pnl) / self.daily_start_capital if self.daily_start_capital > 0 else 0
        
        if self.daily_pnl < 0 and daily_return > self.daily_loss_limit:
            return False, f"Daily loss limit reached ({daily_return * 100:.2f}%)"

        return True, "Trading allowed"

    def check_position_limits(self, portfolio: Portfolio) -> tuple[bool, str]:
        if len(portfolio.positions) >= self.max_positions:
            return False, f"Maximum positions reached ({self.max_positions})"

        return True, "Position check passed"

    def validate_order(self, order: Order, portfolio: Portfolio,
                      current_price: float) -> tuple[bool, str]:
        symbol = order.symbol

        allowed, msg = self.check_trading_allowed(symbol)
        if not allowed:
            return False, msg

        allowed, msg = self.check_position_limits(portfolio)
        if not allowed:
            return False, msg

        position_value = order.quantity * current_price
        allowed, msg = portfolio.check_risk_limits(position_value)
        if not allowed:
            return False, msg

        return True, "Order validated"

    def should_stop_out(self, position: Position, current_price: float,
                       stop_loss_pct: float) -> bool:
        if position.quantity <= 0:
            return False

        if position.side.upper() == 'BUY':
            loss_pct = (position.entry_price - current_price) / position.entry_price
        else:
            loss_pct = (current_price - position.entry_price) / position.entry_price

        return loss_pct >= stop_loss_pct

    def calculate_correlation_risk(self, returns: Dict[str, List[float]]) -> float:
        if len(returns) < 2:
            return 0.0

        symbols = list(returns.keys())
        max_correlation = 0.0

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                r1 = returns[symbols[i]]
                r2 = returns[symbols[j]]
                
                if len(r1) != len(r2) or len(r1) == 0:
                    continue

                mean1 = sum(r1) / len(r1)
                mean2 = sum(r2) / len(r2)
                
                numerator = sum((a - mean1) * (b - mean2) for a, b in zip(r1, r2))
                denom1 = sum((a - mean1) ** 2 for a in r1) ** 0.5
                denom2 = sum((b - mean2) ** 2 for b in r2) ** 0.5
                
                if denom1 > 0 and denom2 > 0:
                    correlation = numerator / (denom1 * denom2)
                    max_correlation = max(max_correlation, abs(correlation))

        return max_correlation

    def get_risk_report(self, portfolio: Portfolio) -> Dict[str, Any]:
        total_exposure = sum(
            pos.quantity * pos.current_price 
            for pos in portfolio.positions.values()
        )
        
        exposure_pct = total_exposure / portfolio.initial_capital if portfolio.initial_capital > 0 else 0
        
        return {
            'daily_pnl': self.daily_pnl,
            'daily_return': self.daily_pnl / self.daily_start_capital if self.daily_start_capital > 0 else 0,
            'total_exposure': total_exposure,
            'exposure_pct': exposure_pct,
            'num_positions': len(portfolio.positions),
            'blocked_symbols': list(self.blocked_symbols),
            'daily_loss_limit': self.daily_loss_limit,
            'max_positions': self.max_positions
        }

class DrawdownTracker:
    def __init__(self):
        self.peak_capital = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.drawdown_start = None
        self.current_drawdown_start = None

    def update(self, current_capital: float, timestamp: int = None):
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
            self.current_drawdown = 0.0
            self.current_drawdown_start = None
        else:
            self.current_drawdown = (self.peak_capital - current_capital) / self.peak_capital
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
                self.drawdown_start = self.current_drawdown_start

    def get_metrics(self) -> Dict[str, Any]:
        return {
            'peak_capital': self.peak_capital,
            'current_drawdown': self.current_drawdown * 100,
            'max_drawdown': self.max_drawdown * 100,
            'drawdown_start': self.drawdown_start
        }
