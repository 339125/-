from typing import Dict, Any, Optional
from ..data.models import Portfolio, Position
from ..utils.logger import logger

class PositionSizer:
    @staticmethod
    def fixed_quantity(capital: float, price: float, quantity: float) -> float:
        return min(quantity, (capital * 0.1) / price)

    @staticmethod
    def percentage_of_capital(capital: float, price: float, 
                              percentage: float = 0.1) -> float:
        return (capital * percentage) / price

    @staticmethod
    def kelly_criterion(capital: float, price: float, win_rate: float,
                       win_loss_ratio: float, fraction: float = 0.25) -> float:
        if win_loss_ratio <= 0 or win_rate <= 0:
            return 0.0
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        kelly = max(0, min(kelly, 0.25))
        return (capital * kelly * fraction) / price

    @staticmethod
    def volatility_based(capital: float, price: float, 
                        atr: float, atr_multiplier: float = 2.0,
                        max_position_pct: float = 0.1) -> float:
        risk_amount = capital * max_position_pct
        stop_loss_distance = atr * atr_multiplier
        position_size = risk_amount / stop_loss_distance
        return min(position_size, (capital * max_position_pct) / price)

class RiskCalculator:
    def __init__(self, max_position_size: float = 0.1,
                 stop_loss: float = 0.05,
                 take_profit: float = 0.1,
                 max_exposure: float = 0.3):
        self.max_position_size = max_position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_exposure = max_exposure

    def calculate_position_size(self, capital: float, price: float,
                               strategy: str = "fixed_pct",
                               **kwargs) -> float:
        if strategy == "fixed_pct":
            return PositionSizer.percentage_of_capital(
                capital, price, self.max_position_size
            )
        elif strategy == "fixed_quantity":
            return PositionSizer.fixed_quantity(
                capital, price, kwargs.get('quantity', 1)
            )
        elif strategy == "kelly":
            return PositionSizer.kelly_criterion(
                capital, price,
                kwargs.get('win_rate', 0.5),
                kwargs.get('win_loss_ratio', 1.5)
            )
        elif strategy == "volatility":
            return PositionSizer.volatility_based(
                capital, price,
                kwargs.get('atr', price * 0.02),
                kwargs.get('atr_multiplier', 2.0)
            )
        return PositionSizer.percentage_of_capital(capital, price, self.max_position_size)

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        if side.upper() == 'BUY':
            return entry_price * (1 - self.stop_loss)
        else:
            return entry_price * (1 + self.stop_loss)

    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        if side.upper() == 'BUY':
            return entry_price * (1 + self.take_profit)
        else:
            return entry_price * (1 - self.take_profit)

    def check_risk_limits(self, portfolio: Portfolio, 
                         new_position_value: float) -> tuple[bool, str]:
        total_exposure = sum(
            pos.quantity * pos.average_entry_price 
            for pos in portfolio.positions.values()
        )

        if new_position_value / portfolio.initial_capital > self.max_position_size:
            return False, f"Position size exceeds maximum ({self.max_position_size * 100}%)"

        if (total_exposure + new_position_value) / portfolio.initial_capital > self.max_exposure:
            return False, f"Total exposure exceeds maximum ({self.max_exposure * 100}%)"

        return True, "Risk check passed"

    def calculate_risk_reward_ratio(self, entry: float, stop: float, 
                                   target: float, side: str) -> float:
        if side.upper() == 'BUY':
            risk = entry - stop
            reward = target - entry
        else:
            risk = stop - entry
            reward = entry - target

        if risk == 0:
            return 0.0
        return reward / risk

    def calculate_var(self, returns: list, confidence: float = 0.95) -> float:
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return abs(sorted_returns[max(0, index)])

    def calculate_portfolio_var(self, positions: Dict[str, Position],
                               prices: Dict[str, float],
                               returns: Dict[str, list],
                               confidence: float = 0.95) -> float:
        portfolio_var = 0.0
        total_value = sum(pos.quantity * prices.get(symbol, 0) 
                        for symbol, pos in positions.items())
        
        if total_value == 0:
            return 0.0

        for symbol, pos in positions.items():
            position_value = pos.quantity * prices.get(symbol, 0)
            weight = position_value / total_value
            symbol_returns = returns.get(symbol, [])
            var = self.calculate_var(symbol_returns, confidence)
            portfolio_var += weight * var

        return portfolio_var * total_value
