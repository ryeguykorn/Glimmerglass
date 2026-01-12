# Tier 0 Quick Reference

## 🚀 Setup (One Time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python ingest_data.py init
```

## 📥 Ingest Data

### Single CSV
```bash
python ingest_data.py ingest data/SPY.csv SPY --timeframe 1min
```

### Bulk Import
```bash
python ingest_data.py bulk data/csvs/ --pattern "*.csv"
```

### From Python
```python
from db.ingest import ingest_csv_to_parquet

parquet_path, dataset_id = ingest_csv_to_parquet(
    csv_path="data/SPY.csv",
    symbol="SPY",
    timeframe="1min"
)
```

## 🔍 Query Data

```python
from db.query import query_time_series, query_latest

# Load date range
df = query_time_series(
    symbol="SPY",
    timeframe="1min",
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# Latest N rows
df = query_latest(symbol="SPY", limit=1000)
```

## 💾 Save Backtest Results

```python
from core.backtest import run_backtest
from db.backtest_store import save_backtest_result

# Load data
df = query_time_series("SPY", "1min")

# Run backtest
result = run_backtest(df, bb_window=20, rsi_window=14, ...)

# Save (automatically stores trades, metrics, config)
run_id = save_backtest_result(
    result=result,
    dataset_id=1,
    config={"bb_window": 20, "rsi_window": 14},
    run_name="My Strategy v1"
)
```

## 📊 Analyze Results

```python
from db.backtest_store import list_recent_runs, compare_backtest_runs

# List recent
df = list_recent_runs(limit=20, symbol="SPY")

# Compare strategies
df = compare_backtest_runs(run_ids=[1, 2, 3])
print(df[["run_name", "total_trades", "win_rate_pct", "total_pnl", "sharpe_ratio"]])
```

## 🔧 CLI Commands

```bash
# List all symbols
python ingest_data.py list

# Show symbol info
python ingest_data.py info SPY --timeframe 1min

# List datasets
python ingest_data.py list --datasets --symbol SPY

# Query from command line
python -m db.query SPY 1min
python -m db.query --list

# View backtest runs
python -m db.backtest_store list
python -m db.backtest_store load 1
python -m db.backtest_store compare 1 2 3
```

## 📁 File Structure

```
data/
├── tier0.db              ← SQLite metadata
└── parquet/              ← Time-series data
    ├── SPY_1min_2023-01-01_2023-12-31.parquet
    └── QQQ_1min_2023-01-01_2023-12-31.parquet
```

## 🎯 Key Benefits

| Feature | Before (CSV) | After (Tier 0) |
|---------|-------------|----------------|
| Load speed | 2-5 seconds | 50-200ms (10-100x faster) |
| Storage | 100 MB | 8-15 MB (85-92% smaller) |
| Query date range | Load full file | Instant metadata query |
| Result tracking | Manual CSV export | Automatic database storage |
| Compare runs | Manual spreadsheet | SQL queries |
| Cost | $0 | $0 |

## 📖 Full Documentation

See [TIER0_README.md](TIER0_README.md) for complete details.

## ⚡ Quick Example

```python
# Complete workflow in ~10 lines
from db.query import query_time_series
from core.backtest import run_backtest
from db.backtest_store import save_backtest_result

# Load data (10-100x faster than CSV)
df = query_time_series("SPY", "1min", start_date="2023-01-01")

# Run backtest
result = run_backtest(df, bb_window=20, rsi_window=14)

# Save results (automatic tracking)
run_id = save_backtest_result(result, dataset_id=1, config={...})

print(f"Saved as run_id={run_id} ✅")
```
