__all__ = ["BinanceAdapter"]

from .base import BaseExchangeAdapter
from typing import List, Dict, Any, Optional
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from ..utils.logger import logger

class BinanceAdapter(BaseExchangeAdapter):
    BASE_URL = "https://api.binance.com/api"
    TESTNET_URL = "https://testnet.binance.vision/api"

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({'X-MBX-APIKEY': api_key})

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, signed: bool = False,
                 params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=10)
                elif method == 'POST':
                    response = self.session.post(url, params=params, timeout=10)
                elif method == 'DELETE':
                    response = self.session.delete(url, params=params, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                else:
                    logger.error(f"API Error: {response.status_code} - {response.text}")
                    return None
            except requests.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def get_klines(self, symbol: str, interval: str, start_time: Optional[int] = None,
                   end_time: Optional[int] = None, limit: int = 500) -> List[Dict[str, Any]]:
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        data = self._request('GET', '/v3/klines', params=params)
        if not data:
            return []

        klines = []
        for k in data:
            klines.append({
                'timestamp': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': k[6],
                'quote_volume': float(k[7]),
                'trades': k[8],
                'taker_buy_base': float(k[9]),
                'taker_buy_quote': float(k[10])
            })
        return klines

    def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        params = {'symbol': symbol, 'limit': limit}
        data = self._request('GET', '/v3/depth', params=params)
        if not data:
            return {'bids': [], 'asks': []}
        return {
            'bids': [[float(p[0]), float(p[1])] for p in data.get('bids', [])],
            'asks': [[float(p[0]), float(p[1])] for p in data.get('asks', [])],
            'last_update_id': data.get('lastUpdateId')
        }

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        params = {'symbol': symbol}
        data = self._request('GET', '/v3/ticker/24hr', params=params)
        if not data:
            return {}
        return {
            'symbol': data.get('symbol'),
            'last_price': float(data.get('lastPrice', 0)),
            'bid_price': float(data.get('bidPrice', 0)),
            'ask_price': float(data.get('askPrice', 0)),
            'volume': float(data.get('volume', 0)),
            'quote_volume': float(data.get('quoteVolume', 0)),
            'price_change': float(data.get('priceChange', 0)),
            'price_change_percent': float(data.get('priceChangePercent', 0)),
            'high': float(data.get('highPrice', 0)),
            'low': float(data.get('lowPrice', 0))
        }

    def get_account_balance(self) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {'balances': []}
        data = self._request('GET', '/v3/account', signed=True)
        if not data:
            return {'balances': []}
        balances = []
        for asset in data.get('balances', []):
            if float(asset.get('free', 0)) > 0 or float(asset.get('locked', 0)) > 0:
                balances.append({
                    'asset': asset.get('asset'),
                    'free': float(asset.get('free', 0)),
                    'locked': float(asset.get('locked', 0))
                })
        return {'balances': balances}

    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            logger.warning("No API credentials provided, order simulation mode")
            return {
                'order_id': f"sim_{int(time.time() * 1000)}",
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'price': price,
                'quantity': quantity,
                'status': 'NEW',
                'simulated': True
            }

        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        if price:
            params['price'] = price
            params['timeInForce'] = 'GTC'

        data = self._request('POST', '/v3/order', signed=True, params=params)
        if not data:
            return {'error': 'Failed to place order'}
        return {
            'order_id': str(data.get('orderId')),
            'symbol': data.get('symbol'),
            'side': data.get('side'),
            'type': data.get('type'),
            'price': float(data.get('price', 0)),
            'quantity': float(data.get('origQty', 0)),
            'status': data.get('status'),
            'executed_qty': float(data.get('executedQty', 0))
        }

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {'order_id': order_id, 'status': 'CANCELED', 'simulated': True}

        params = {'symbol': symbol, 'orderId': order_id}
        data = self._request('DELETE', '/v3/order', signed=True, params=params)
        if not data:
            return {'error': 'Failed to cancel order'}
        return {
            'order_id': str(data.get('orderId')),
            'status': data.get('status')
        }

    def get_exchange_info(self) -> Dict[str, Any]:
        data = self._request('GET', '/v3/exchangeInfo')
        return data or {}
