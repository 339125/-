__all__ = ["BaseExchangeAdapter"]

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BaseExchangeAdapter(ABC):
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = ""

    @abstractmethod
    def get_klines(self, symbol: str, interval: str, start_time: Optional[int] = None, 
                   end_time: Optional[int] = None, limit: int = 10000) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        pass

    def _validate_symbol(self, symbol: str) -> bool:
        return len(symbol) >= 6 and symbol.isupper()

    def _parse_timestamp(self, timestamp: Any) -> int:
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        elif isinstance(timestamp, datetime):
            return int(timestamp.timestamp() * 1000)
        return int(timestamp)
