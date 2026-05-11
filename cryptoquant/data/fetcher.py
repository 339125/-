from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from ..exchange_adapters.base import BaseExchangeAdapter
from .models import Candlestick
from .cache import cache_manager
from ..utils.logger import logger

class MarketDataFetcher:
    def __init__(self, exchange_adapter: BaseExchangeAdapter):
        self.exchange = exchange_adapter

    def fetch_klines(self, symbol: str, interval: str, 
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: int = 1000,
                     use_cache: bool = True) -> List[Candlestick]:
        start_time = None
        end_time = None

        if start_date:
            start_time = self._parse_date(start_date)
        if end_date:
            end_time = self._parse_date(end_date)

        cache_key = f"klines_{symbol}_{interval}_{start_time}_{end_time}"
        if use_cache and cache_manager.has(cache_key):
            logger.info(f"Using cached data for {symbol} {interval}")
            return cache_manager.get(cache_key)

        all_klines = []
        current_start = start_time

        while True:
            klines = self.exchange.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=end_time,
                limit=limit
            )

            if not klines:
                break

            for k in klines:
                all_klines.append(Candlestick(
                    timestamp=k['timestamp'],
                    open=k['open'],
                    high=k['high'],
                    low=k['low'],
                    close=k['close'],
                    volume=k['volume']
                ))

            last_timestamp = klines[-1]['timestamp']

            if end_time and last_timestamp >= end_time:
                break

            if len(klines) < limit:
                break

            current_start = last_timestamp + 1

        if use_cache and all_klines:
            cache_manager.set(cache_key, all_klines)

        logger.info(f"Fetched {len(all_klines)} klines for {symbol} {interval}")
        return all_klines

    def fetch_klines_dataframe(self, symbol: str, interval: str,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               limit: int = 1000) -> pd.DataFrame:
        klines = self.fetch_klines(symbol, interval, start_date, end_date, limit)

        if not klines:
            return pd.DataFrame()

        data = {
            'timestamp': [k.timestamp for k in klines],
            'open': [k.open for k in klines],
            'high': [k.high for k in klines],
            'low': [k.low for k in klines],
            'close': [k.close for k in klines],
            'volume': [k.volume for k in klines]
        }

        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        return df

    def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        cache_key = f"orderbook_{symbol}_{limit}"
        if cache_manager.has(cache_key):
            return cache_manager.get(cache_key)

        order_book = self.exchange.get_order_book(symbol, limit)
        if order_book:
            cache_manager.set(cache_key, order_book, duration=5)

        return order_book

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        cache_key = f"ticker_{symbol}"
        if cache_manager.has(cache_key):
            return cache_manager.get(cache_key)

        ticker = self.exchange.get_ticker(symbol)
        if ticker:
            cache_manager.set(cache_key, ticker, duration=10)

        return ticker

    def get_historical_data(self, symbol: str, interval: str, 
                           days: int = 30) -> pd.DataFrame:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.fetch_klines_dataframe(
            symbol=symbol,
            interval=interval,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )

    def _parse_date(self, date_str: str) -> int:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        except ValueError:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return int(dt.timestamp() * 1000)
            except ValueError:
                logger.error(f"Invalid date format: {date_str}")
                return int(datetime.now().timestamp() * 1000)

    def validate_data(self, klines: List[Candlestick]) -> List[Candlestick]:
        validated = []
        for k in klines:
            if (k.high >= k.low and 
                k.high >= k.open and k.high >= k.close and
                k.low <= k.open and k.low <= k.close and
                k.volume >= 0):
                validated.append(k)
            else:
                logger.warning(f"Invalid candlestick data at {k.timestamp}")

        return validated

    def resample_data(self, df: pd.DataFrame, 
                     new_interval: str) -> pd.DataFrame:
        rule_map = {
            '5m': '5T', '15m': '15T', '30m': '30T',
            '1h': '1H', '2h': '2H', '4h': '4H',
            '1d': '1D', '1w': '1W'
        }

        rule = rule_map.get(new_interval, '1H')

        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        return resampled.dropna()
