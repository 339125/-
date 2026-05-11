import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from cryptoquant.backtesting import BacktestEngine, BacktestConfig
from cryptoquant.strategies import MovingAverageCrossover, RSIStrategy, MACDStrategy
from cryptoquant.data.models import Candlestick
from cryptoquant.utils.logger import logger

def generate_sample_data(symbol="BTCUSDT", days=180, interval='1h'):
    print(f"Generating sample {symbol} data for {days} days...")
    
    num_candles = days * 24 if interval == '1h' else days * 24 * 4
    base_price = 25000
    volatility = 0.02
    
    dates = pd.date_range(end=datetime.now(), periods=num_candles, freq='h')
    prices = [base_price]
    
    for i in range(1, num_candles):
        change = np.random.normal(0, volatility)
        trend = 0.0001
        price = prices[-1] * (1 + change + trend)
        prices.append(price)
    
    prices = np.array(prices)
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, num_candles)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, num_candles)))
    opens = prices * (1 + np.random.normal(0, 0.005, num_candles))
    volumes = np.random.uniform(100, 1000, num_candles)
    
    klines = []
    for i in range(num_candles):
        klines.append(Candlestick(
            timestamp=int(dates[i].timestamp() * 1000),
            open=float(opens[i]),
            high=float(highs[i]),
            low=float(lows[i]),
            close=float(prices[i]),
            volume=float(volumes[i])
        ))
    
    return klines

def create_sample_dataframe(klines):
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

def test_backtest_engine():
    print("="*60)
    print("CryptoQuant - Backtest Engine Test")
    print("="*60)
    
    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005
    )
    
    klines = generate_sample_data("BTCUSDT", days=180)
    df = create_sample_dataframe(klines)
    
    print(f"\nGenerated {len(df)} candlesticks")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df, config

def test_ma_crossover_strategy(df, engine):
    print("\n" + "="*60)
    print("Testing Moving Average Crossover Strategy")
    print("="*60)
    
    strategy = MovingAverageCrossover(
        symbol="BTCUSDT",
        short_period=10,
        long_period=30
    )
    
    results = engine.run(
        strategy=strategy,
        symbol="BTCUSDT",
        start_date=df.index[0].strftime('%Y-%m-%d'),
        end_date=df.index[-1].strftime('%Y-%m-%d'),
        interval='1h',
        data=df
    )
    
    results.print_summary()
    return results

def test_rsi_strategy(df, engine):
    print("\n" + "="*60)
    print("Testing RSI Strategy")
    print("="*60)
    
    engine.initialize()
    
    strategy = RSIStrategy(
        symbol="BTCUSDT",
        period=14,
        overbought=70.0,
        oversold=30.0
    )
    
    results = engine.run(
        strategy=strategy,
        symbol="BTCUSDT",
        start_date=df.index[0].strftime('%Y-%m-%d'),
        end_date=df.index[-1].strftime('%Y-%m-%d'),
        interval='1h',
        data=df
    )
    
    results.print_summary()
    return results

def test_macd_strategy(df, engine):
    print("\n" + "="*60)
    print("Testing MACD Strategy")
    print("="*60)
    
    engine.initialize()
    
    strategy = MACDStrategy(
        symbol="BTCUSDT",
        fast_period=12,
        slow_period=26,
        signal_period=9
    )
    
    results = engine.run(
        strategy=strategy,
        symbol="BTCUSDT",
        start_date=df.index[0].strftime('%Y-%m-%d'),
        end_date=df.index[-1].strftime('%Y-%m-%d'),
        interval='1h',
        data=df
    )
    
    results.print_summary()
    return results

def test_strategy_comparison():
    print("\n" + "="*60)
    print("Strategy Comparison Summary")
    print("="*60)
    
    df, config = test_backtest_engine()
    
    strategies_results = []
    
    engine1 = BacktestEngine(config=config)
    ma_results = test_ma_crossover_strategy(df, engine1)
    strategies_results.append(('MA Crossover', ma_results))
    
    engine2 = BacktestEngine(config=config)
    rsi_results = test_rsi_strategy(df, engine2)
    strategies_results.append(('RSI', rsi_results))
    
    engine3 = BacktestEngine(config=config)
    macd_results = test_macd_strategy(df, engine3)
    strategies_results.append(('MACD', macd_results))
    
    print("\n" + "="*60)
    print("Final Comparison Table")
    print("="*60)
    print(f"{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades':<8}")
    print("-"*60)
    
    for name, results in strategies_results:
        print(f"{name:<20} {results.total_return:>8.2f}%  {results.sharpe_ratio:>8.2f}  "
              f"{results.max_drawdown:>8.2f}%  {results.total_trades:>6}")
    
    print("="*60)

def test_data_fetcher():
    print("\n" + "="*60)
    print("Testing Data Models and Utilities")
    print("="*60)
    
    from cryptoquant.data.models import Candlestick, Position, Signal, Order
    
    c = Candlestick(
        timestamp=1234567890000,
        open=25000.0,
        high=25100.0,
        low=24900.0,
        close=25050.0,
        volume=100.0
    )
    print(f"\nCandlestick Test: {c.symbol if hasattr(c, 'symbol') else 'N/A'}")
    print(f"  Open: ${c.open}, High: ${c.high}, Low: ${c.low}, Close: ${c.close}")
    print(f"  Volume: {c.volume}")
    
    pos = Position(symbol="BTCUSDT", quantity=0.1, average_entry_price=25000)
    print(f"\nPosition Test:")
    print(f"  Symbol: {pos.symbol}, Quantity: {pos.quantity}, Entry: ${pos.average_entry_price}")
    
    signal = Signal(
        timestamp=1234567890000,
        symbol="BTCUSDT",
        side="BUY",
        strength=1.0
    )
    print(f"\nSignal Test:")
    print(f"  {signal.side} {signal.symbol} @ strength {signal.strength}")
    
    order = Order(
        order_id="test_001",
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=0.1,
        price=25000.0
    )
    print(f"\nOrder Test:")
    print(f"  {order.order_id}: {order.side} {order.quantity} {order.symbol} @ ${order.price}")

def main():
    try:
        test_data_fetcher()
        
        test_strategy_comparison()
        
        print("\n" + "="*60)
        print("All Tests Completed Successfully!")
        print("="*60)
        
        print("\nUsage Examples:")
        print("-"*60)
        print("# Run backtest with CLI:")
        print("python -m cryptoquant.main backtest -s ma_crossover -m BTCUSDT")
        print()
        print("# Fetch data:")
        print("python -m cryptoquant.main data -m BTCUSDT --start-date 2024-01-01")
        print()
        print("# List strategies:")
        print("python -m cryptoquant.main strategies")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
