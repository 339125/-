import os
import yaml
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            'exchanges': {
                'binance': {
                    'api_key': os.getenv('BINANCE_API_KEY', ''),
                    'api_secret': os.getenv('BINANCE_API_SECRET', ''),
                    'testnet': True,
                    'base_url': 'https://testnet.binance.vision/api'
                },
                'gate': {
                    'api_key': os.getenv('GATE_API_KEY', ''),
                    'api_secret': os.getenv('GATE_API_SECRET', ''),
                    'testnet': True,
                    'base_url': 'https://api.gateio.ws/api/v4'
                }
            },
            'backtesting': {
                'initial_capital': 10000,
                'commission': 0.001,
                'slippage': 0.0005
            },
            'risk': {
                'max_position_size': 0.1,
                'stop_loss': 0.05,
                'take_profit': 0.1
            },
            'data': {
                'cache_duration': 300,
                'data_dir': 'data'
            }
        }

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def save(self):
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

config = Config()
