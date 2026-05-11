from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"

@dataclass
class Candlestick:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: Optional[int] = None
    quote_volume: Optional[float] = None
    trades: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)

@dataclass
class OrderBook:
    bids: List[List[float]]
    asks: List[List[float]]
    last_update_id: Optional[int] = None
    timestamp: Optional[int] = None

    def get_mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0][0] + self.asks[0][0]) / 2

    def get_spread(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return self.asks[0][0] - self.bids[0][0]

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    status: str = "NEW"
    filled_quantity: float = 0.0
    average_price: float = 0.0
    timestamp: Optional[int] = None
    commission: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price
        }

@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    average_entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    def get_value(self, current_price: float) -> float:
        return self.quantity * current_price

    def update_entry_price(self, new_quantity: float, new_price: float):
        total_cost = (self.quantity * self.average_entry_price) + (new_quantity * new_price)
        self.quantity += new_quantity
        if self.quantity > 0:
            self.average_entry_price = total_cost / self.quantity
        else:
            self.average_entry_price = 0.0

@dataclass
class Signal:
    timestamp: int
    symbol: str
    side: str
    strength: float = 1.0
    quantity: Optional[float] = None
    price: Optional[float] = None
    strategy_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'side': self.side,
            'strength': self.strength,
            'quantity': self.quantity,
            'price': self.price,
            'strategy': self.strategy_name
        }

@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    commission: float = 0.0
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'quantity': self.quantity,
            'commission': self.commission,
            'timestamp': self.timestamp
        }

@dataclass
class Portfolio:
    initial_capital: float
    current_capital: float
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    def get_total_value(self, prices: Dict[str, float]) -> float:
        position_value = sum(
            pos.quantity * prices.get(symbol, 0) 
            for symbol, pos in self.positions.items()
        )
        return self.current_capital + position_value

    def update_equity(self, timestamp: int, prices: Dict[str, float]):
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.get_total_value(prices)
        })
