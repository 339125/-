__all__ = ["GateAdapter"]

from .base import BaseExchangeAdapter
from typing import List, Dict, Any, Optional
import requests
import time
import hmac
import hashlib
from ..utils.logger import logger

class GateAdapter(BaseExchangeAdapter):
    BASE_URL = "https://api.gateio.ws/api/v4"
    TESTNET_URL = "https://api.gateio.ws/api/v4"

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'KEY': api_key
        })

    def _generate_signature(self, method: str, url: str, query_string: str = "", 
                           payload: str = "") -> str:
        hashed_payload = hashlib.sha512(payload.encode('utf-8')).hexdigest()
        message = f"{method}\n{url}\n{query_string}\n{hashed_payload}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, signed: bool = False,
                params: Optional[Dict[str, Any]] = None, data: Optional[str] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        query_string = ""
        if params and method == 'GET':
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        headers = {}
        if signed:
            payload = data if data else ""
            signature = self._generate_signature(method, endpoint, query_string, payload)
            headers['SIGN'] = signature

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = self.session.get(url, headers=headers, timeout=10)
                elif method == 'POST':
                    response = self.session.post(url, headers=headers, data=data, timeout=10)
                elif method == 'DELETE':
                    response = self.session.delete(url, headers=headers, timeout=10)
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
                   end_time: Optional[int] = None, limit: int = 10000) -> List[Dict[str, Any]]:
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h',
            '8h': '8h', '12h': '12h', '1d': '1d', '3d': '3d', '1w': '7d'
        }
        gate_interval = interval_map.get(interval, '1h')
        currency_pair = symbol.replace('USDT', '_USDT')

        params = {'currency_pair': currency_pair, 'interval': gate_interval, 'limit': limit}
        if start_time:
            params['from'] = start_time // 1000
        if end_time:
            params['to'] = end_time // 1000

        data = self._request('GET', '/spot/candlesticks', params=params)
        if not data:
            return []

        klines = []
        for k in data:
            klines.append({
                'timestamp': k[0] * 1000,
                'volume': float(k[1]),
                'close': float(k[2]),
                'high': float(k[3]),
                'low': float(k[4]),
                'open': float(k[5]),
                'trade_vol': float(k[6]),
                'trade_vol_quote': float(k[7])
            })
        return klines

    def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        currency_pair = symbol.replace('USDT', '_USDT')
        params = {'currency_pair': currency_pair, 'limit': limit}
        data = self._request('GET', '/spot/order_book', params=params)
        if not data:
            return {'bids': [], 'asks': []}
        return {
            'bids': [[float(p[0]), float(p[1])] for p in data.get('bids', [])],
            'asks': [[float(p[0]), float(p[1])] for p in data.get('asks', [])],
            'last_update_id': data.get('id', 0)
        }

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        currency_pair = symbol.replace('USDT', '_USDT')
        endpoint = f'/spot/tickers?currency_pair={currency_pair}'
        data = self._request('GET', endpoint)
        if not data or not isinstance(data, list) or len(data) == 0:
            return {}
        ticker = data[0]
        return {
            'symbol': symbol,
            'last_price': float(ticker.get('last', 0)),
            'bid_price': float(ticker.get('highest_bid', 0)),
            'ask_price': float(ticker.get('lowest_ask', 0)),
            'volume': float(ticker.get('base_volume', 0)),
            'quote_volume': float(ticker.get('quote_volume', 0)),
            'price_change': float(ticker.get('change', 0)),
            'high': float(ticker.get('high_24h', 0)),
            'low': float(ticker.get('low_24h', 0))
        }

    def get_account_balance(self) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {'balances': []}
        import json
        data = self._request('GET', '/spot/accounts', signed=True)
        if not data:
            return {'balances': []}
        balances = []
        for asset in data:
            if float(asset.get('available', 0)) > 0 or float(asset.get('locked', 0)) > 0:
                balances.append({
                    'asset': asset.get('currency'),
                    'free': float(asset.get('available', 0)),
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
                'status': 'open',
                'simulated': True
            }

        currency_pair = symbol.replace('USDT', '_USDT')
        import json
        order_data = {
            'currency_pair': currency_pair,
            'side': side.lower(),
            'type': order_type.lower(),
            'amount': str(quantity)
        }
        if price:
            order_data['price'] = str(price)

        payload = json.dumps(order_data)
        data = self._request('POST', '/spot/orders', signed=True, data=payload)
        if not data or 'id' not in data:
            return {'error': 'Failed to place order'}
        return {
            'order_id': str(data.get('id')),
            'symbol': symbol,
            'side': data.get('side'),
            'type': data.get('type'),
            'price': float(data.get('price', 0)),
            'quantity': float(data.get('amount', 0)),
            'status': data.get('status'),
            'executed_qty': float(data.get('filled_notional', 0))
        }

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {'order_id': order_id, 'status': 'cancelled', 'simulated': True}

        currency_pair = symbol.replace('USDT', '_USDT')
        data = self._request('DELETE', f'/spot/orders/{order_id}', signed=True,
                             params={'currency_pair': currency_pair})
        if not data:
            return {'error': 'Failed to cancel order'}
        return {
            'order_id': str(data.get('id')),
            'status': data.get('status')
        }

    def get_exchange_info(self) -> Dict[str, Any]:
        data = self._request('GET', '/spot/currencies')
        return {'currencies': data or []}
