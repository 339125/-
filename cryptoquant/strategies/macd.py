from typing import Optional
import pandas as pd
from .base import BaseStrategy
from ..data.models import Signal

class MACDStrategy(BaseStrategy):
    def __init__(self, symbol: str = "BTCUSDT",
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9,
                 quantity: Optional[float] = None):
        super().__init__("MACD_Strategy")
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.quantity = quantity
        self.position = 0
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period
        }

    def on_init(self):
        self.position = 0

    def on_data(self, data: pd.DataFrame, symbol: str) -> Optional[Signal]:
        if len(data) < self.slow_period + self.signal_period:
            return None

        close = data['close']
        macd_data = self.calculate_macd(close, self.fast_period, 
                                       self.slow_period, self.signal_period)
        macd = macd_data['macd']
        signal = macd_data['signal']
        histogram = macd_data['histogram']

        prev_hist = histogram.iloc[-2]
        curr_hist = histogram.iloc[-1]
        prev_macd = macd.iloc[-2]
        curr_macd = macd.iloc[-1]
        prev_signal = signal.iloc[-2]
        curr_signal = signal.iloc[-1]

        golden_cross = (prev_macd <= prev_signal and curr_macd > curr_signal and curr_hist > 0)
        death_cross = (prev_macd >= prev_signal and curr_macd < curr_signal and curr_hist < 0)

        if golden_cross:
            if self.position != 1:
                self.position = 1
                return self.create_signal(
                    symbol=symbol,
                    side='BUY',
                    strength=1.0,
                    quantity=self.quantity,
                    price=close.iloc[-1]
                )

        elif death_cross:
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
