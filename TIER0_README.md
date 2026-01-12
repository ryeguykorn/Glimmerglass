# Tier 0: Local Development Database Layer

**SQLite + Parquet + DuckDB** for cost-free, high-performance time-series storage.

## Architecture

```
Tier 0 Components:
├── SQLite (metadata)         ← Symbols, datasets, backtest runs
├── Parquet (time-series)     ← OHLCV data, compressed with ZSTD
└── DuckDB (analytics)        ← Fast queries on Parquet files
```

**When to use Tier 0:**
- ✅ Local development
- ✅ Single-user backtesting
- ✅ Up to ~10M rows (a few GB of data)
- ✅ No server costs ($0/month)

**Upgrade to Tier 1 when:**
- ❌ Need multi-user access
- ❌ Data exceeds 10GB
- ❌ Want remote access
- ❌ Need scheduled jobs

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies for Tier 0:
- `duckdb>=0.9.0` - Analytics engine
- `pyarrow>=14.0.0` - Parquet file format

### 2. Initialize Database

```bash
python ingest_data.py init
```

Creates `data/tier0.db` (SQLite) and `data/parquet/` directory.

### 3. Ingest Your Data

#### Option A: Single CSV

```bash
python ingest_data.py ingest data/SPY.csv SPY --timeframe 1min
```

#### Option B: Bulk Ingest Directory

```bash
python ingest_data.py bulk data/csvs/ --pattern "*.csv"
```

#### Option C: Programmatic (from Python)

```python
from db.ingest import ingest_csv_to_parquet

parquet_path, dataset_id = ingest_csv_to_parquet(
    csv_path="data/SPY.csv",
    symbol="SPY",
    timeframe="1min"
)
```

### 4. Query Data

```python
from db.query import query_time_series

# Load data for backtesting
df = query_time_series(
    symbol="SPY",
    timeframe="1min",
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

### 5. Save Backtest Results

```python
from core.backtest import run_backtest
from db.backtest_store import save_backtest_result

# Run backtest (existing code)
result = run_backtest(df, ...)

# Save to database
run_id = save_backtest_result(
    result=result,
    dataset_id=1,
    config={
        "bb_window": 20,
        "rsi_window": 14,
        # ... other parameters
    },
    run_name="SPY 2023 - 20BB + 14RSI"
)

print(f"Saved as run_id={run_id}")
```

---

## File Structure

```
Glimmerglass.WebApp/
├── data/
│   ├── tier0.db                    ← SQLite metadata
│   └── parquet/                    ← Time-series data
│       ├── SPY_1min_2023-01-01_2023-12-31.parquet
│       └── QQQ_1min_2023-01-01_2023-12-31.parquet
├── db/
│   ├── __init__.py
│   ├── schema.py                   ← SQLite schema + helpers
│   ├── ingest.py                   ← CSV → Parquet ingestion
│   ├── query.py                    ← DuckDB-powered queries
│   └── backtest_store.py           ← Backtest result storage
└── ingest_data.py                  ← CLI tool
```

---

## CLI Reference

### Initialize Database

```bash
python ingest_data.py init
```

Creates SQLite database and tables.

### Ingest Single CSV

```bash
python ingest_data.py ingest <csv_path> <symbol> [options]

Options:
  --timeframe TEXT     Timeframe (default: 1min)
  --asset-type TEXT    Asset type (default: equity)
  --vendor TEXT        Data vendor (default: csv_import)
  --output PATH        Output directory for parquet files
  --db PATH            SQLite database path

Example:
  python ingest_data.py ingest data/SPY.csv SPY --timeframe 1min
```

### Bulk Ingest

```bash
python ingest_data.py bulk <directory> [options]

Options:
  --pattern TEXT       Filename pattern (default: *)
  --timeframe TEXT     Timeframe for all files
  --asset-type TEXT    Asset type for all files

Example:
  python ingest_data.py bulk data/csvs/ --pattern "*.csv"
```

### List Symbols

```bash
python ingest_data.py list

# List datasets for a specific symbol
python ingest_data.py list --datasets --symbol SPY
```

### Show Symbol Info

```bash
python ingest_data.py info SPY --timeframe 1min
```

Output:
```
📈 SPY @ 1min
   Rows: 1,234,567
   Datasets: 1
   Date Range: 2023-01-01 → 2023-12-31
   Total Size: 45.2 MB
```

---

## Python API

### Query Time-Series Data

```python
from db.query import query_time_series

# Load data for date range
df = query_time_series(
    symbol="SPY",
    timeframe="1min",
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# Load latest N rows
from db.query import query_latest
df = query_latest(symbol="SPY", limit=1000)

# Get summary without loading data
from db.query import query_date_range_summary
summary = query_date_range_summary("SPY", "1min")
# Returns: {row_count, datasets, start_date, end_date, total_size_mb}
```

### Resample Data

```python
from db.query import resample_time_series

# Convert 1min → 5min
df = resample_time_series(
    symbol="SPY",
    source_timeframe="1min",
    target_timeframe="5min",
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

### Save Backtest Results

```python
from db.backtest_store import save_backtest_result, list_recent_runs

# Save result
run_id = save_backtest_result(
    result=backtest_result,    # BacktestResult from core.backtest
    dataset_id=1,
    config={"bb_window": 20, "rsi_window": 14},
    run_name="My Strategy v1"
)

# List recent runs
df = list_recent_runs(limit=20, symbol="SPY")

# Load a previous run
from db.backtest_store import load_backtest_result
data = load_backtest_result(run_id=5)
# Returns: {run metadata, config, trades list}

# Compare multiple runs
from db.backtest_store import compare_backtest_runs
df = compare_backtest_runs(run_ids=[1, 2, 3])
```

### Export Results

```python
from db.backtest_store import export_backtest_to_json, export_trades_to_csv

# Export full run to JSON
export_backtest_to_json(run_id=5, output_path="results/run5.json")

# Export trades to CSV
export_trades_to_csv(run_id=5, output_path="results/run5_trades.csv")
```

---

## Database Schema

### `symbols` table
Tracks available symbols (SPY, QQQ, etc.)

```sql
CREATE TABLE symbols (
    symbol_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    asset_type TEXT NOT NULL,
    vendor TEXT NOT NULL,
    description TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

### `datasets` table
Tracks Parquet files containing time-series data

```sql
CREATE TABLE datasets (
    dataset_id INTEGER PRIMARY KEY,
    symbol_id INTEGER,
    timeframe TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_size_bytes INTEGER NOT NULL,
    checksum TEXT,
    created_at TEXT,
    FOREIGN KEY (symbol_id) REFERENCES symbols(symbol_id)
);
```

### `backtest_runs` table
Stores backtest run metadata

```sql
CREATE TABLE backtest_runs (
    run_id INTEGER PRIMARY KEY,
    dataset_id INTEGER,
    run_name TEXT,
    config_json TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_trades INTEGER NOT NULL,
    win_rate REAL,
    avg_pnl REAL,
    total_pnl REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    runtime_seconds REAL,
    created_at TEXT,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);
```

### `trades` table
Individual trades from backtest runs

```sql
CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY,
    run_id INTEGER,
    entry_date TEXT NOT NULL,
    exit_date TEXT NOT NULL,
    days_held INTEGER,
    pnl REAL NOT NULL,
    pnl_pct REAL,
    status TEXT NOT NULL,
    entry_reason TEXT,
    exit_reason TEXT,
    strike_width REAL,
    distance_from_price REAL,
    iv_rank REAL,
    created_at TEXT,
    FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
);
```

---

## Performance

**Storage Efficiency:**
- CSV: 100 MB → Parquet (ZSTD): 8-15 MB (85-92% compression)
- 1M rows @ 1-minute: ~12 MB compressed

**Query Speed:**
- DuckDB on Parquet: 10-100x faster than Pandas CSV loading
- 1M row scan: ~50-200ms (vs 2-5 seconds for CSV)

**Recommended Limits:**
- Max rows per dataset: 10M (single Parquet file)
- Max total storage: 10-20 GB (Tier 0 sweet spot)
- Beyond this → Upgrade to Tier 1 (Postgres + VPS)

---

## Migration from CSV Workflow

### Before (CSV-based):

```python
import pandas as pd

# Load CSV
df = pd.read_csv("data/SPY.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Run backtest
result = run_backtest(df, ...)

# Export results
result.to_csv("results.csv")
```

### After (Tier 0):

```python
from db.query import query_time_series
from db.backtest_store import save_backtest_result

# Load from Parquet (faster)
df = query_time_series(symbol="SPY", timeframe="1min")

# Run backtest (unchanged)
result = run_backtest(df, ...)

# Save to database (automatic)
run_id = save_backtest_result(
    result=result,
    dataset_id=1,
    config={...},
    run_name="SPY 2023"
)
```

**Benefits:**
- ✅ 3-10x faster data loading
- ✅ Automatic result tracking
- ✅ Easy comparison across runs
- ✅ Query by date range without loading full file
- ✅ Reusable datasets (ingest once, query many times)

---

## Workflow Example

### 1. One-time setup

```bash
# Initialize
python ingest_data.py init

# Ingest your CSV data
python ingest_data.py ingest data/SPY_2023.csv SPY --timeframe 1min
```

### 2. Daily backtesting

```python
from db.query import query_time_series
from core.backtest import run_backtest
from db.backtest_store import save_backtest_result

# Load data
df = query_time_series("SPY", "1min", start_date="2023-01-01")

# Run backtest
result = run_backtest(
    df,
    bb_window=20,
    rsi_window=14,
    # ... other params
)

# Save results
run_id = save_backtest_result(
    result=result,
    dataset_id=1,
    config={"bb_window": 20, "rsi_window": 14},
    run_name="SPY 2023 - Strategy v1"
)
```

### 3. Compare strategies

```python
from db.backtest_store import compare_backtest_runs

# Compare runs 1, 2, 3
df = compare_backtest_runs([1, 2, 3])
print(df[["run_name", "total_trades", "win_rate_pct", "total_pnl", "sharpe_ratio"]])
```

Output:
```
           run_name  total_trades  win_rate_pct  total_pnl  sharpe_ratio
0  Strategy v1               245         67.35    12340.50         1.234
1  Strategy v2               312         71.15    15678.90         1.456
2  Strategy v3               198         64.14     9876.40         1.123
```

---

## Advanced Usage

### Custom Database Location

```python
from pathlib import Path
from db.schema import get_connection, init_database

# Use custom database path
db_path = Path("/custom/location/my_backtest.db")
conn = get_connection(db_path)
init_database(conn)
conn.close()

# Use with query functions
from db.query import query_time_series
df = query_time_series("SPY", "1min", db_path=db_path)
```

### Programmatic Ingestion (API data)

```python
import pandas as pd
from db.ingest import ingest_dataframe

# Fetch from API or generate data
df = pd.DataFrame({
    "timestamp": pd.date_range("2024-01-01", periods=1000, freq="1min"),
    "open": [100.0] * 1000,
    "high": [101.0] * 1000,
    "low": [99.0] * 1000,
    "close": [100.5] * 1000,
    "volume": [10000] * 1000
})

# Ingest directly
parquet_path, dataset_id = ingest_dataframe(
    df=df,
    symbol="TEST",
    timeframe="1min",
    vendor="api"
)
```

---

## Troubleshooting

### "No datasets found"

**Problem:** Query returns no results.

**Solution:** Check that data was ingested:
```bash
python ingest_data.py list
```

### "Missing required columns"

**Problem:** CSV doesn't have expected columns.

**Solution:** Ensure CSV has these columns:
- `timestamp` (required)
- `open`, `high`, `low`, `close`, `volume` (required)

### DuckDB errors

**Problem:** `duckdb` module not found.

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Parquet file not found

**Problem:** File path in database doesn't exist.

**Solution:** Check `datasets` table:
```python
from db.schema import get_connection, get_datasets
conn = get_connection()
datasets = get_datasets(conn)
print(datasets)
```

---

## Cost Analysis

| Component | Storage | Cost |
|-----------|---------|------|
| SQLite | ~1 MB | $0 |
| Parquet (1M rows) | ~12 MB | $0 |
| Parquet (10M rows) | ~120 MB | $0 |
| Total (10M rows) | ~150 MB | **$0/month** |

**When to upgrade to Tier 1:**
- Data exceeds 10GB → VPS ($5-20/month)
- Need remote access → Postgres on VPS
- Multi-user → Server required

---

## Next Steps

✅ **You now have Tier 0 set up!**

**Ready to use:**
1. Ingest your CSV data with `ingest_data.py`
2. Query with `db.query` module
3. Run backtests and save with `db.backtest_store`

**Optional upgrades:**
- **Tier 1**: Postgres + VPS ($5-20/month) → Multi-user, remote access
- **Tier 2**: Cloud (S3 + Lambda) → Billions of rows, serverless

See the main architecture document for Tier 1/2 setup instructions.

---

## Support

Questions? Check:
- [Main README](README.md) - App usage
- Architecture docs - Tier 1/2 upgrade paths
- `db/` module docstrings - API details
