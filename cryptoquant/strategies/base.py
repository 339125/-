from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd
from ..data.models import Signal

class BaseStrategy(ABC):
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.params: Dict[str, Any] = {}
        self.indicators: Dict[str, pd.Series] = {}
        self.data: Optional[pd.DataFrame] = None
        self.symbol: str = ""
        self.last_signal: Optional[Signal] = None

    @abstractmethod
    def on_init(self):
        """策略初始化"""
        pass

    @abstractmethod
    def on_data(self, data: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """处理新的K线数据"""
        pass

    def set_params(self, **kwargs):
        """设置策略参数"""
        self.params.update(kwargs)

    def get_param(self, key: str, default: Any = None) -> Any:
        """获取策略参数"""
        return self.params.get(key, default)

    def calculate_indicator(self, name: str, data: pd.Series) -> pd.Series:
        """计算并缓存技术指标"""
        self.indicators[name] = data
        return data

    def get_indicator(self, name: str) -> Optional[pd.Series]:
        """获取缓存的技术指标"""
        return self.indicators.get(name)

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return data.rolling(window=period).mean()

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """计算指数移动平均线"""
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """计算相对强弱指数"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, data: pd.Series, fast: int = 12, 
                      slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_bollinger_bands(self, data: pd.Series, 
                                 period: int = 20, 
                                 std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """计算布林带"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    def calculate_atr(self, high: pd.Series, low: pd.Series, 
                     close: pd.Series, period: int = 14) -> pd.Series:
        """计算平均真实波幅"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def calculate_stochastic(self, high: pd.Series, low: pd.Series,
                            close: pd.Series, k_period: int = 14,
                            d_period: int = 3) -> Dict[str, pd.Series]:
        """计算随机指标"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_line = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_line = k_line.rolling(window=d_period).mean()
        return {
            'k': k_line,
            'd': d_line
        }

    def create_signal(self, symbol: str, side: str, strength: float = 1.0,
                     quantity: Optional[float] = None, 
                     price: Optional[float] = None) -> Signal:
        """创建交易信号"""
        from ..data.models import Signal
        timestamp = int(pd.Timestamp.now().timestamp() * 1000)
        signal = Signal(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            strength=strength,
            quantity=quantity,
            price=price,
            strategy_name=self.name
        )
        self.last_signal = signal
        return signal

    def print_signal(self, signal: Signal):
        """打印信号信息"""
        print(f"[{self.name}] Signal: {signal.side} {signal.symbol} "
              f"@ {signal.price or 'MARKET'} (strength: {signal.strength})")
