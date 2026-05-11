import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptoquant.exchange_adapters import BinanceAdapter, GateAdapter
from cryptoquant.backtesting import BacktestEngine, BacktestConfig
from cryptoquant.strategies import MovingAverageCrossover, RSIStrategy, MACDStrategy
from cryptoquant.data.fetcher import MarketDataFetcher

def demo_backtest():
    print("="*60)
    print("CryptoQuant Demo - Quantitative Trading System")
    print("="*60)

    exchange = BinanceAdapter(testnet=True)

    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005
    )

    engine = BacktestEngine(exchange, config)

    strategy = MovingAverageCrossover(
        symbol="BTCUSDT",
        short_period=10,
        long_period=30
    )

    print("\nRunning backtest with MA Crossover Strategy...")
    print(f"Symbol: BTCUSDT")
    print(f"Period: 2024-01-01 to 2024-06-30")
    print(f"Interval: 1h")
    print(f"Initial Capital: $10,000")

    results = engine.run(
        strategy=strategy,
        symbol="BTCUSDT",
        start_date="2024-01-01",
        end_date="2024-06-30",
        interval="1h"
    )

    results.print_summary()

    print("\n" + "="*60)
    print("Demo completed successfully!")
    print("="*60)

if __name__ == "__main__":
    demo_backtest()
