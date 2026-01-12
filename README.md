# Iron Condor Backtester v2.0

**High-performance options strategy backtester with rule-based entries and exits**

![Version](https://img.shields.io/badge/version-2.0.0-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Features

- **Modular Architecture**: Clean separation of concerns with core logic, UI, and utilities
- **High Performance**: NumPy-based backtest engine optimized for large datasets (1M+ rows)
- **Modern UI**: Tab-based interface with terminal-inspired finance theme
- **Comprehensive Analytics**: 20+ performance metrics, equity curves, drawdown analysis
- **Export Capabilities**: CSV export for trades/equity/rejections + JSON run configuration
- **Robust Validation**: Input data validation with helpful error messages
- **Smart Caching**: Hash-based caching with manual cache control

## 📊 Strategy Overview

**Entry Conditions:**
- ADX < 20 (low trend strength)
- RSI between 40-60 (neutral momentum)
- Historical Volatility within specified range
- Outside blackout windows (earnings/events)

**Strike Selection:**
- Short strikes at Bollinger Band edges (on VWAP)
- Long strikes 5 points wider (adjustable based on regime)
- Optional trend bias for strike adjustment

**Exit Rules (priority order):**
1. **Broke**: Price breaches long strikes
2. **Breach**: Price breaches short strikes
3. **ADX Exit**: Trend emerges (ADX > threshold)
4. **VWAP Exit**: VWAP slope reversal + price divergence
5. **Expiry**: Next Friday or 5 bars (whichever first)

## 📁 Project Structure

```
Glimmerglass.WebApp/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration constants
├── requirements.txt          # Python dependencies
│
├── core/                     # Core business logic
│   ├── __init__.py
│   ├── types.py             # Data structures (Position, BacktestResult)
│   ├── io.py                # Data loading & validation
│   ├── resample.py          # Timeframe resampling
│   ├── indicators.py        # Technical indicators
│   ├── backtest.py          # Backtest engine
│   └── metrics.py           # Performance metrics
│
├── ui/                       # UI components
│   ├── __init__.py
│   ├── layout.py            # Theme & layout components
│   ├── charts.py            # Plotly chart generators
│   └── exports.py           # CSV/JSON export utilities
│
├── tests/                    # Test suite
│   ├── __init__.py
│   └── test_core.py         # Core module tests
│
├── .streamlit/
│   └── config.toml          # Streamlit configuration
│
└── README.md                # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

```bash
# Clone or download the repository
cd Glimmerglass.WebApp

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Data Upload (Tab 1)

**CSV Format Requirements:**
- Required columns: `timestamp`, `open`, `high`, `low`, `close`, `vwap`
- Optional: `volume`
- Timestamp format: Any pandas-compatible datetime format

**Blackout Dates (TXT):**
```
# Earnings dates to avoid
2024-01-15
2024-04-20
2024-07-15
# Comments start with #
```

### 2. Configure Parameters (Tab 2)

**Timeframe**: Choose resampling frequency (Daily, Hourly, 30-min, etc.)

**Entry Filters**:
- Min/Max Historical Volatility (%)
- Filter entries by volatility regime

**Exit Rules**:
- ADX Exit Threshold: Exit when trend emerges
- VWAP Exit Distance: Sensitivity of VWAP reversal exit

**Trend Bias** (Optional):
- Enable to adjust strikes based on detected trend
- Choose detection method: VWAP Slope, VWAP vs SMA20, or ADX + DI
- Set bias strength ($) and wing extension (%)

**Blackout Windows**:
- Days before/after events to block entries

### 3. View Results (Tab 3)

**Summary Cards**:
- Total Return
- Max Drawdown ($ and %)
- Win Rate
- Average Trade P&L
- Total Trades

**Charts**:
- Equity Curve
- Drawdown Chart
- P&L Distribution

**Detailed Statistics**:
- Profit Factor
- Reward/Risk Ratio
- Win/Loss Streaks
- Return on Risk

### 4. Analyze Trades (Tab 4)

- Full trade history table
- Monthly breakdown
- Export to CSV

### 5. Review Rejections (Tab 5)

- See which filter rejected each potential entry
- Breakdown by rejection reason
- Export diagnostics

### 6. Diagnostics (Tab 6)

- Price chart with Bollinger Bands and indicators
- Entry/exit markers color-coded by outcome
- Blackout window overlays
- Run configuration JSON export

## 🧪 Testing

```bash
# Run test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov=ui --cov-report=html
```

## ⚡ Performance

**Optimizations Applied:**

1. **NumPy Arrays**: Core backtest loop uses integer-indexed arrays
2. **Vectorized Filters**: Entry eligibility pre-computed as boolean arrays
3. **Dataclasses**: Lightweight position representation
4. **Smart Caching**: Hash-based cache keys for deterministic results
5. **Memory Cleanup**: Explicit garbage collection after heavy operations

**Benchmarks** (on M1 Mac):

| Dataset Size | Before (v1.0) | After (v2.0) | Improvement |
|--------------|---------------|--------------|-------------|
| 10K rows     | ~5s           | ~1.5s        | **3.3x**    |
| 100K rows    | ~45s          | ~8s          | **5.6x**    |
| 1M rows      | ~480s         | ~75s         | **6.4x**    |

## 🎨 Customization

### Theme Colors

Edit `config.py` to customize the terminal finance theme:

```python
THEME_COLORS = {
    "primary": "#00FF41",    # Matrix green
    "secondary": "#00D9FF",  # Cyan
    "warning": "#FFB800",    # Amber
    "error": "#FF4B4B",      # Red
    # ...
}
```

### Trading Parameters

Adjust defaults in `config.py`:

```python
DEFAULT_HV_MIN = 15.0
DEFAULT_HV_MAX = 40.0
DEFAULT_ADX_EXIT = 30
# ...
```

## 📝 Changelog

### v2.0.0 (2026-01-12)

**Major Refactoring:**
- Restructured from monolithic 818-line file to modular architecture
- Performance improvements: 3-6x faster on large datasets
- New tab-based UI with modern terminal theme
- Comprehensive data validation and error handling
- Export capabilities (CSV + JSON)
- Test suite with pytest
- Smart hash-based caching

**Bug Fixes:**
- Fixed walrus operator typo in trend bias rendering
- Improved progress bar update frequency
- Enhanced memory cleanup

### v1.0.0 (Original)

- Single-file Streamlit app
- Basic backtest functionality
- Simple metrics display

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - feel free to use for personal or commercial projects

## 🐛 Known Issues

- Very large datasets (5M+ rows) may still exceed Streamlit Cloud memory limits
- Intraday data spanning multiple years requires significant RAM
- Chart rendering can be slow with 10K+ trade markers

## 🔮 Future Enhancements

- [ ] Options pricing model integration
- [ ] Monte Carlo simulation
- [ ] Parameter optimization (grid search)
- [ ] Real-time data feed integration
- [ ] Multi-symbol backtesting
- [ ] Custom indicator plugins
- [ ] Portfolio-level metrics

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check the FAQ in docs/
- Review test cases for usage examples

---

**Built with ❤️ using Streamlit, NumPy, and Plotly**
