import re
from typing import List, Dict, Any

class Validators:
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        pattern = r'^[A-Z]{2,10}(USDT|BTC|ETH|BNB)$'
        return bool(re.match(pattern, symbol))

    @staticmethod
    def validate_interval(interval: str) -> bool:
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']
        return interval in valid_intervals

    @staticmethod
    def validate_quantity(quantity: float) -> bool:
        return quantity > 0

    @staticmethod
    def validate_price(price: float) -> bool:
        return price > 0

    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> bool:
        from datetime import datetime
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            return start < end
        except ValueError:
            return False

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        errors = []
        required_keys = ['exchanges', 'backtesting', 'risk']
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required config key: {key}")
        return errors

validators = Validators()
