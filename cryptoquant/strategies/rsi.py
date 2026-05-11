from typing import Optional
import pandas as pd
from .base import BaseStrategy
from ..data.models import Signal

class RSIStrategy(BaseStrategy):
    def __init__(self, symbol: str = "BTCUSDT",
                 period: int = 14,
                 overbought: float = 70.0,
                 oversold: float = 30.0,
                 quantity: Optional[float] = None):
        super().__init__("RSI_Strategy")
        self.symbol = symbol
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.quantity = quantity
        self.position = 0
        self.params = {
            'period': period,
            'overbought': overbought,
            'oversold': oversold
        }

    def on_init(self):
        self.position = 0

    def on_data(self, data: pd.DataFrame, symbol: str) -> Optional[Signal]:
        if len(data) < self.period + 1:
            return None

        close = data['close']
        rsi = self.calculate_rsi(close, self.period)

        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        if prev_rsi < self.oversold and current_rsi >= self.oversold:
            if self.position != 1:
                self.position = 1
                return self.create_signal(
                    symbol=symbol,
                    side='BUY',
                    strength=(current_rsi - self.oversold) / (100 - self.oversold),
                    quantity=self.quantity,
                    price=close.iloc[-1]
                )

        elif prev_rsi > self.overbought and current_rsi <= self.overbought:
            if self.position != -1:
                self.position = -1
                return self.create_signal(
                    symbol=symbol,
                    side='SELL',
                    strength=(self.overbought - current_rsi) / self.overbought,
                    quantity=self.quantity,
                    price=close.iloc[-1]
                )

        return None
