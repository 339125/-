# CryptoQuant - 加密货币量化交易系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

**一个功能完整的加密货币量化交易系统，支持回测、实盘交易和可视化分析**

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用文档](#使用文档) • [策略示例](#策略示例)

</div>

---

## 📖 项目简介

CryptoQuant 是一个模块化的加密货币量化交易系统，支持币安（Binance）和 Gate.io 两大交易所。系统提供完整的回测引擎、多种交易策略、风险管理模块以及类似 TradingView 的 Web 可视化界面。

## ✨ 功能特性

### 🔌 交易所支持
- **币安（Binance）**：支持现货交易、K线数据获取、订单管理
- **Gate.io**：支持现货交易、K线数据获取、订单管理
- 统一的 API 接口，方便扩展其他交易所

### 📊 回测引擎
- 完整的历史数据回测功能
- 支持滑点和手续费模拟
- 详细的性能指标计算（夏普比率、最大回撤、胜率等）
- 资金曲线追踪

### 📈 交易策略
- **均线交叉策略（MA Crossover）**：短期/长期均线交叉信号
- **RSI 策略**：超买超卖反转策略
- **MACD 策略**：MACD 信号线交叉策略
- 可轻松扩展自定义策略

### 🎯 风险管理
- 多种仓位计算方法（固定比例、凯利公式、波动率调整）
- 止损止盈设置
- 最大持仓限制
- 每日亏损限制

### 🖥️ Web 可视化界面
- 类似 TradingView 的专业界面
- K线图表（支持缩放、平移）
- 技术指标叠加（MA、RSI、MACD）
- 交易信号标记
- 响应式设计（支持 PC 和手机）

## 🚀 快速开始

### 环境要求
- Python 3.10+
- pip 包管理器

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行回测

```bash
# 使用 CLI 运行回测
python -m cryptoquant.main backtest \
    --strategy ma_crossover \
    --symbol BTCUSDT \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --capital 10000
```

### 启动 Web 界面

```bash
# 方式1：直接打开 HTML 文件
open cryptoquant/dashboard.html

# 方式2：启动本地服务器
cd cryptoquant && python -m http.server 8000
# 访问 http://localhost:8000/dashboard.html
```

## 📚 使用文档

### Python API

```python
from cryptoquant import BacktestEngine, BacktestConfig
from cryptoquant.strategies import MovingAverageCrossover
from cryptoquant.exchange_adapters import BinanceAdapter

# 创建交易所适配器
exchange = BinanceAdapter(testnet=True)

# 配置回测参数
config = BacktestConfig(
    initial_capital=10000,
    commission=0.001,
    slippage=0.0005
)

# 创建回测引擎
engine = BacktestEngine(exchange, config)

# 创建策略
strategy = MovingAverageCrossover(
    symbol="BTCUSDT",
    short_period=10,
    long_period=30
)

# 运行回测
results = engine.run(
    strategy=strategy,
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    interval="1h"
)

# 查看结果
results.print_summary()
```

### 自定义策略

```python
from cryptoquant.strategies import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, symbol="BTCUSDT"):
        super().__init__("MyStrategy")
        self.symbol = symbol
    
    def on_init(self):
        # 初始化策略参数
        self.position = 0
    
    def on_data(self, data, symbol):
        # 处理K线数据，生成交易信号
        close = data['close']
        
        # 你的交易逻辑
        if self.should_buy(close):
            return self.create_signal(
                symbol=symbol,
                side='BUY',
                strength=1.0
            )
        
        return None
```

## 📈 策略示例

### 回测结果对比

| 策略 | 收益率 | 夏普比率 | 最大回撤 | 交易次数 |
|------|--------|---------|---------|----------|
| MA 交叉 | +5.08% | 0.14 | -10.11% | 159 |
| RSI | +0.14% | 0.06 | -0.63% | 85 |
| MACD | -0.99% | -0.01 | -9.91% | 349 |

## 📁 项目结构

```
cryptoquant/
├── __init__.py
├── config.py              # 配置管理
├── main.py                # CLI 入口
├── dashboard.html         # Web 可视化界面
├── exchange_adapters/     # 交易所适配器
│   ├── base.py
│   ├── binance.py
│   └── gate.py
├── data/                  # 数据层
│   ├── models.py
│   ├── fetcher.py
│   └── cache.py
├── backtesting/           # 回测引擎
│   ├── engine.py
│   └── performance.py
├── strategies/            # 交易策略
│   ├── base.py
│   ├── ma_crossover.py
│   ├── rsi.py
│   └── macd.py
├── risk_management/       # 风险管理
│   ├── position_sizing.py
│   └── risk_controls.py
└── utils/                 # 工具函数
    ├── logger.py
    └── validators.py
```

## ⚙️ 配置说明

创建 `config.yaml` 文件：

```yaml
exchanges:
  binance:
    api_key: "your_api_key"
    api_secret: "your_api_secret"
    testnet: true
  gate:
    api_key: "your_api_key"
    api_secret: "your_api_secret"
    testnet: true

backtesting:
  initial_capital: 10000
  commission: 0.001
  slippage: 0.0005

risk:
  max_position_size: 0.1
  stop_loss: 0.05
  take_profit: 0.1
```

## 🔧 CLI 命令

```bash
# 运行回测
python -m cryptoquant.main backtest -s ma_crossover -m BTCUSDT

# 获取历史数据
python -m cryptoquant.main data -m BTCUSDT --start-date 2024-01-01

# 查看可用策略
python -m cryptoquant.main strategies
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本项目仅供学习和研究使用。加密货币交易存在高风险，可能导致资金损失。请谨慎使用，作者不对任何交易损失负责。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！**

Made with ❤️ by CryptoQuant Team

</div>
