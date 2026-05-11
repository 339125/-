from typing import Optional
import pandas as pd
from .base import BaseStrategy
from ..data.models import Signal

class MovingAverageCrossover(BaseStrategy):
    def __init__(self, symbol: str = "BTCUSDT", 
                 short_period: int = 10, 
                 long_period: int = 30,
                 quantity: Optional[float] = None):
        super().__init__("MA_Crossover")
        self.symbol = symbol
        self.short_period = short_period
        self.long_period = long_period
        self.quantity = quantity
        self.position = 0
        self.params = {
            'short_period': short_period,
            'long_period': long_period
        }

    def on_init(self):
        self.position = 0

    def on_data(self, data: pd.DataFrame, symbol: str) -> Optional[Signal]:
        if len(data) < self.long_period:
            return None

        close = data['close']
        short_ma = self.calculate_sma(close, self.short_period)
        long_ma = self.calculate_sma(close, self.long_period)

        if short_ma.iloc[-2] <= long_ma.iloc[-2] and short_ma.iloc[-1] > long_ma.iloc[-1]:
            if self.position != 1:
                self.position = 1
                return self.create_signal(
                    symbol=symbol,
                    side='BUY',
                    strength=1.0,
                    quantity=self.quantity,
                    price=close.iloc[-1]
                )

        elif short_ma.iloc[-2] >= long_ma.iloc[-2] and short_ma.iloc[-1] < long_ma.iloc[-1]:
            if self.position != -1:
                self.position = -1
                return self.create_signal(
                    symbol=symbol,
                    side='SELL',
                    strength=1.0,
                    quantity=self.quantity,
                    price=close.iloc[-1]
                )

        return None
