import argparse
import sys
from typing import Optional
from .exchange_adapters import BinanceAdapter, GateAdapter
from .backtesting import BacktestEngine, BacktestConfig
from .strategies import MovingAverageCrossover, RSIStrategy, MACDStrategy
from .data.fetcher import MarketDataFetcher
from .utils.logger import logger

STRATEGIES = {
    'ma_crossover': MovingAverageCrossover,
    'rsi': RSIStrategy,
    'macd': MACDStrategy
}

def run_backtest(args):
    exchange = create_exchange(args.exchange, args.api_key, args.api_secret, args.testnet)
    if not exchange:
        logger.error("Failed to create exchange adapter")
        return

    config = BacktestConfig(
        initial_capital=args.capital,
        commission=args.commission,
        slippage=args.slippage
    )

    engine = BacktestEngine(exchange, config)

    strategy_class = STRATEGIES.get(args.strategy)
    if not strategy_class:
        logger.error(f"Unknown strategy: {args.strategy}")
        print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
        return

    strategy = strategy_class(
        symbol=args.symbol,
        quantity=args.quantity
    )

    logger.info(f"Running backtest: {args.strategy} on {args.symbol}")
    logger.info(f"Period: {args.start_date} to {args.end_date}")
    logger.info(f"Initial Capital: ${args.capital}")

    results = engine.run(
        strategy=strategy,
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        interval=args.interval
    )

    results.print_summary()

    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        logger.info(f"Results saved to {args.output}")

def fetch_data(args):
    exchange = create_exchange(args.exchange, args.api_key, args.api_secret, False)
    if not exchange:
        logger.error("Failed to create exchange adapter")
        return

    fetcher = MarketDataFetcher(exchange)
    df = fetcher.fetch_klines_dataframe(
        symbol=args.symbol,
        interval=args.interval,
        start_date=args.start_date,
        end_date=args.end_date
    )

    if df.empty:
        logger.error("No data fetched")
        return

    logger.info(f"Fetched {len(df)} rows of data")
    print(df.tail(10))

    if args.output:
        df.to_csv(args.output)
        logger.info(f"Data saved to {args.output}")

def list_strategies(args):
    print("\nAvailable Strategies:")
    print("-" * 50)
    for name, strategy_class in STRATEGIES.items():
        print(f"  {name}")
        print(f"    Description: {strategy_class.__doc__ or 'No description'}")
        print()

def create_exchange(exchange_name: str, api_key: str = "", 
                   api_secret: str = "", testnet: bool = True):
    if exchange_name.lower() == 'binance':
        return BinanceAdapter(api_key, api_secret, testnet)
    elif exchange_name.lower() == 'gate':
        return GateAdapter(api_key, api_secret, testnet)
    else:
        logger.error(f"Unknown exchange: {exchange_name}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='CryptoQuant - Cryptocurrency Quantitative Trading System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--strategy', '-s', 
                               choices=list(STRATEGIES.keys()),
                               default='ma_crossover',
                               help='Trading strategy')
    backtest_parser.add_argument('--symbol', '-m', default='BTCUSDT',
                               help='Trading symbol')
    backtest_parser.add_argument('--exchange', '-e', default='binance',
                               choices=['binance', 'gate'],
                               help='Exchange')
    backtest_parser.add_argument('--start-date', default='2024-01-01',
                               help='Start date (YYYY-MM-DD)')
    backtest_parser.add_argument('--end-date', default='2024-12-31',
                               help='End date (YYYY-MM-DD)')
    backtest_parser.add_argument('--interval', '-i', default='1h',
                               choices=['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
                               help='Time interval')
    backtest_parser.add_argument('--capital', '-c', type=float, default=10000,
                               help='Initial capital')
    backtest_parser.add_argument('--commission', type=float, default=0.001,
                               help='Commission rate')
    backtest_parser.add_argument('--slippage', type=float, default=0.0005,
                               help='Slippage rate')
    backtest_parser.add_argument('--quantity', type=float, default=None,
                               help='Fixed quantity per trade')
    backtest_parser.add_argument('--api-key', default='',
                               help='Exchange API key')
    backtest_parser.add_argument('--api-secret', default='',
                               help='Exchange API secret')
    backtest_parser.add_argument('--testnet', action='store_true',
                               help='Use testnet')
    backtest_parser.add_argument('--output', '-o',
                               help='Output file for results')

    data_parser = subparsers.add_parser('data', help='Fetch market data')
    data_parser.add_argument('--symbol', '-m', default='BTCUSDT',
                            help='Trading symbol')
    data_parser.add_argument('--exchange', '-e', default='binance',
                            choices=['binance', 'gate'],
                            help='Exchange')
    data_parser.add_argument('--start-date', default='2024-01-01',
                            help='Start date (YYYY-MM-DD)')
    data_parser.add_argument('--end-date', default='2024-12-31',
                            help='End date (YYYY-MM-DD)')
    data_parser.add_argument('--interval', '-i', default='1h',
                            choices=['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
                            help='Time interval')
    data_parser.add_argument('--api-key', default='',
                            help='Exchange API key')
    data_parser.add_argument('--api-secret', default='',
                            help='Exchange API secret')
    data_parser.add_argument('--output', '-o',
                            help='Output CSV file')

    strategy_parser = subparsers.add_parser('strategies', 
                                           help='List available strategies')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'backtest':
        run_backtest(args)
    elif args.command == 'data':
        fetch_data(args)
    elif args.command == 'strategies':
        list_strategies(args)

if __name__ == '__main__':
    main()
