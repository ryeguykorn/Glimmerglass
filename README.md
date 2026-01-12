# Glimmerglass Iron Condor Backtester

A sophisticated options backtesting platform for Iron Condor strategies, built with Streamlit and featuring a Tier 0 database architecture for efficient OHLC data management.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.52+-red)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running the Application](#running-the-application)
- [Database Management](#database-management)
- [Deployment](#deployment)
- [Auto-Deploy Setup](#auto-deploy-setup)
- [Project Structure](#project-structure)
- [Strategy Overview](#strategy-overview)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

### 🎯 Backtesting Engine
- **Iron Condor Strategy**: Automated backtesting with configurable parameters
- **Real-time visualization**: Interactive charts using Plotly
- **Risk metrics**: Calculate max profit, max loss, win rate, and P&L statistics
- **Portfolio simulation**: Test strategies across different market conditions
- **High performance**: NumPy-based engine optimized for large datasets (1M+ rows)

### 💾 Tier 0 Database
- **Hybrid architecture**: SQLite metadata + Parquet files + DuckDB queries
- **Web-based data upload**: CSV file upload interface for OHLC data
- **Dataset management**: View, load, and delete datasets via UI
- **Optimized storage**: Efficient Parquet compression for time-series data

### 📊 Analysis Tools
- **Position Greeks**: Track Delta, Gamma, Vega, Theta
- **P&L tracking**: Daily and cumulative profit/loss analysis
- **Volatility analysis**: VIX-based market regime detection
- **Performance metrics**: Sharpe ratio, max drawdown, win/loss ratios
- **Export capabilities**: CSV export for trades, equity curves, and rejections

---

## 🏗️ Architecture

### Tier 0 Database Design

```
┌─────────────────────────────────────────────┐
│           Streamlit Application             │
│                  (app.py)                   │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    ┌────▼────┐         ┌────▼────┐
    │ SQLite  │         │ DuckDB  │
    │ Metadata│◄────────┤ Query   │
    │         │         │ Engine  │
    └────┬────┘         └────┬────┘
         │                   │
         └─────────┬─────────┘
                   │
         ┌─────────▼─────────┐
         │  Parquet Files    │
         │  (OHLC Data)      │
         └───────────────────┘
```

**Components:**
- **SQLite**: Stores dataset metadata (symbol, timeframe, record count, date range)
- **Parquet**: Stores actual OHLC time-series data (compressed, columnar format)
- **DuckDB**: Zero-copy queries directly on Parquet files (no data duplication)

---

## 🔧 Prerequisites

- **Python 3.11+** (tested on 3.13)
- **Git** (for version control)
- **GitHub account** (for deployment)
- **Streamlit Cloud account** (free, for hosting)

---

## 🚀 Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ryeguykorn/Glimmerglass.git
cd Glimmerglass
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Core Dependencies:**
- `streamlit>=1.52.0` - Web framework
- `duckdb>=0.9.0` - Query engine
- `pyarrow>=14.0.0` - Parquet file support
- `plotly>=5.17.0` - Interactive charts
- `numpy`, `pandas` - Data manipulation
- `scipy` - Statistical calculations

### 4. Initialize the Database

The database is automatically initialized on first run, but you can manually initialize:

```bash
python3 -c "from db.schema import init_database; init_database()"
```

This creates:
- `data/tier0.db` - SQLite database
- `data/parquet/` - Directory for Parquet files

---

## 🎮 Running the Application

### Start the Development Server

```bash
# Using virtual environment Python
.venv/bin/streamlit run app.py

# Or if venv is activated:
streamlit run app.py
```

The app will start at: **http://localhost:8501**

### Accessing Different Tabs

1. **💾 Database** - Upload and manage OHLC datasets
2. **📊 Backtest** - Run Iron Condor backtests
3. **📈 Analysis** - View P&L and performance metrics
4. **⚙️ Settings** - Configure strategy parameters

---

## 💾 Database Management

### Uploading Data

1. Navigate to the **Database** tab
2. Click **"Browse files"** and select a CSV file
3. CSV must include these columns:
   - `timestamp` (datetime)
   - `open` (float)
   - `high` (float)
   - `low` (float)
   - `close` (float)
   - `volume` (int/float)
4. Enter **Symbol** (e.g., `SPY`, `QQQ`)
5. Select **Timeframe** (1min, 5min, 15min, etc.)
6. Click **"Ingest Data"**

### Viewing Datasets

The **Available Datasets** table shows:
- Symbol and timeframe
- Date range (first/last dates)
- Number of records
- File size

### Loading Data for Backtesting

1. Use the **"Load Dataset"** section
2. Select symbol and timeframe from dropdowns
3. Data automatically loads for backtesting

### Deleting Datasets

1. Expand **"Delete Dataset"** section
2. Select dataset to remove
3. Click **"Delete"** (removes both SQLite entry and Parquet file)

### Programmatic Data Upload

```python
from db.ingest import ingest_dataframe
import pandas as pd

# Load your data
df = pd.read_csv('your_data.csv')

# Ingest into database
ingest_dataframe(
    df=df,
    symbol='SPY',
    timeframe='1min',
    overwrite=True  # Replace if exists
)
```

---

## 🌐 Deployment

### Deploy to Streamlit Cloud (Free)

#### Step 1: Push Code to GitHub

```bash
# If not already initialized
git init
git add .
git commit -m "Initial commit"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

#### Step 2: Deploy on Streamlit Cloud

1. Go to **https://share.streamlit.io/**
2. Sign in with GitHub
3. Click **"Create app"**
4. Fill in the form:
   - **Repository**: `YOUR_USERNAME/YOUR_REPO`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: Choose your subdomain (e.g., `glimmerglass`)
5. Click **"Deploy!"**

#### Step 3: Wait for Deployment

- Initial deployment takes **3-5 minutes**
- Streamlit Cloud will:
  - Install dependencies from `requirements.txt`
  - Start the application
  - Assign a public URL: `https://YOUR_SUBDOMAIN.streamlit.app`

#### Step 4: Verify Deployment

- Visit your public URL
- Test all tabs (Database, Backtest, Analysis)
- Upload a sample dataset

### Making Updates

After deployment, any push to GitHub automatically redeploys:

```bash
# Make your code changes
git add .
git commit -m "Description of changes"
git push

# Streamlit Cloud detects the push and redeploys (~2-3 minutes)
```

---

## 🤖 Auto-Deploy Setup

For automatic Git commits and pushes on file changes:

### 1. Start Auto-Deploy Watcher

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the auto-deploy script
python auto_deploy.py
```

### 2. How It Works

- **Watches** all `.py` files in the project
- **Detects** changes when you save files
- **Waits** 10 seconds (cooldown period)
- **Commits** changes with automatic message
- **Pushes** to GitHub
- **Triggers** Streamlit Cloud redeployment

### 3. What's Ignored

Auto-deploy ignores:
- `.git/` directory
- `__pycache__/` directories
- `.venv/` virtual environment
- `data/tier0.db` (database file)
- `.pyc` compiled Python files
- `.DS_Store` (macOS files)

### 4. Stop Auto-Deploy

Press `Ctrl+C` in the terminal running `auto_deploy.py`

### 5. Manual Deployment (Alternative)

If you prefer manual control:

```bash
git add .
git commit -m "Your commit message"
git push
```

---

## 📁 Project Structure

```
Glimmerglass/
├── app.py                  # Main Streamlit application
├── config.py               # Configuration settings
├── benchmark.py            # Performance benchmarking
├── auto_deploy.py          # Auto-deploy watcher
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── db/                    # Tier 0 Database modules
│   ├── __init__.py
│   ├── schema.py          # SQLite schema and CRUD operations
│   ├── ingest.py          # Data ingestion (CSV → Parquet)
│   ├── query.py           # DuckDB query interface
│   └── backtest_store.py  # Backtest result storage
│
├── core/                  # Core business logic
│   ├── __init__.py
│   ├── types.py          # Data structures (Position, BacktestResult)
│   ├── io.py             # Data loading & validation
│   ├── logic.py          # Iron condor position management
│   ├── backtest.py       # Backtest engine with Greeks calculation
│   └── analytics.py      # Performance metrics and trade analysis
│
├── ui/                   # Streamlit interface
│   ├── __init__.py
│   ├── components.py     # Reusable UI widgets
│   ├── pages.py          # Tab content (backtest, analysis, settings)
│   └── theme.py          # Custom styling and CSS
│
├── data/                 # Database files (gitignored)
│   ├── tier0.db         # SQLite metadata
│   └── parquet/         # Parquet data files
│       ├── SPY_1min_20240101_20241231.parquet
│       └── ...
│
├── tests/                # Test suite
│   ├── __init__.py
│   └── test_core.py     # Core module tests
│
├── .streamlit/
│   └── config.toml      # Streamlit configuration
│
├── public/              # Static files
│   └── Index.html
│
└── .venv/               # Virtual environment (gitignored)
```

---

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

---

## 🤝 Contributing

### Development Workflow

1. **Create a branch** for your feature
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** and test locally
   ```bash
   streamlit run app.py
   ```

3. **Commit changes**
   ```bash
   git add .
   git commit -m "Add: description of your changes"
   ```

4. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Add docstrings to functions
- Keep functions focused and modular

### Testing

Run tests before committing:

```bash
pytest
pytest --cov=db tests/  # With coverage
```

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors

**Solution**: Ensure you're using the virtual environment:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Database not initializing

**Solution**: Manually initialize:
```bash
python3 -c "from db.schema import init_database; init_database()"
```

### Issue: Streamlit Cloud deployment fails

**Common causes:**
- Wrong main file path (should be `app.py`)
- Wrong branch name (should be `main`)
- Repository is private (make it public in GitHub settings)
- Missing dependencies in `requirements.txt`

**Check logs** in Streamlit Cloud dashboard for specific errors.

### Issue: Auto-deploy not detecting changes

**Solution**: 
- Ensure `auto_deploy.py` is running (`python auto_deploy.py`)
- Check you're editing files in the project directory
- Verify the file isn't in the ignore list

### Issue: Data not persisting on Streamlit Cloud

**Expected behavior**: Streamlit Cloud uses ephemeral storage. The database resets on each deployment. 

**For persistent storage:**
- Use Streamlit Cloud secrets for database connection strings
- Connect to external database (PostgreSQL, Supabase, etc.)
- Store data in cloud storage (AWS S3, Google Cloud Storage)

### Issue: CSV upload errors

**Common causes:**
- Missing required columns (timestamp, open, high, low, close, volume)
- Incorrect datetime format in timestamp column
- Non-numeric values in OHLC/volume columns

**Solution**: Validate your CSV format
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

---

## 📚 Database Schema

### SQLite Metadata Table

```sql
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    parquet_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe)
);
```

### Parquet File Schema

| Column    | Type      | Description                    |
|-----------|-----------|--------------------------------|
| timestamp | datetime  | Bar timestamp (UTC)            |
| open      | float     | Opening price                  |
| high      | float     | Highest price in period        |
| low       | float     | Lowest price in period         |
| close     | float     | Closing price                  |
| volume    | int/float | Trading volume                 |

---

## 📚 Additional Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **DuckDB Docs**: https://duckdb.org/docs
- **Plotly Docs**: https://plotly.com/python
- **Options Greeks**: https://www.investopedia.com/options-greeks-4694784

---

## 📝 License

This project is for educational and research purposes.

---

## 👤 Author

Built by Ryan

**Repository**: https://github.com/ryeguykorn/Glimmerglass

**Deployed App**: https://YOUR_SUBDOMAIN.streamlit.app (after deployment)

---

## 🎯 Quick Start Summary

```bash
# 1. Clone and setup
git clone https://github.com/ryeguykorn/Glimmerglass.git
cd Glimmerglass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run locally
streamlit run app.py

# 3. Deploy (after pushing to GitHub)
# - Go to share.streamlit.io
# - Click "Create app"
# - Enter: ryeguykorn/Glimmerglass, main, app.py
# - Click "Deploy!"

# 4. Auto-deploy (optional)
python auto_deploy.py
```

---

**Questions or Issues?**  
Open an issue on GitHub or contact the maintainer.

**Happy Backtesting! 🚀**


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
