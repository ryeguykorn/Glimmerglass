# ✅ Tier 0 Checklist

Use this checklist to start using your new database layer.

## Initial Setup (One Time)

- [x] Install dependencies: `pip install -r requirements.txt`
- [x] Initialize database: `python ingest_data.py init`
- [x] Verify setup: `python -m db.schema` should show tables created

## Ingest Your Data

Choose one:

- [ ] **Option A - Single CSV:**
  ```bash
  python ingest_data.py ingest data/YOUR_FILE.csv SYMBOL --timeframe 1min
  ```

- [ ] **Option B - Bulk directory:**
  ```bash
  python ingest_data.py bulk data/csvs/ --pattern "*.csv"
  ```

- [ ] **Option C - Programmatic:**
  ```python
  from db.ingest import ingest_csv_to_parquet
  parquet_path, dataset_id = ingest_csv_to_parquet("data/file.csv", "SPY", "1min")
  ```

- [ ] **Verify ingestion:**
  ```bash
  python ingest_data.py list
  ```

## Update Your Workflow

### Before (CSV):
```python
df = pd.read_csv("data/SPY.csv")
```

### After (Tier 0):
```python
from db.query import query_time_series
df = query_time_series("SPY", "1min")
```

- [ ] Replace CSV loading with `query_time_series()`
- [ ] Test that your backtest still runs
- [ ] Verify performance improvement

## Add Result Tracking

```python
from db.backtest_store import save_backtest_result

# After running backtest
run_id = save_backtest_result(
    result=result,
    dataset_id=1,  # Get this from ingestion or db.schema.get_datasets()
    config={"bb_window": 20, "rsi_window": 14, ...},
    run_name="My Strategy - SPY 2023"
)

print(f"Saved as run_id={run_id}")
```

- [ ] Add `save_backtest_result()` after backtest runs
- [ ] Give descriptive names to your runs
- [ ] Store complete config for reproducibility

## Compare Strategies

```python
from db.backtest_store import list_recent_runs, compare_backtest_runs

# List all runs
df = list_recent_runs(limit=20)
print(df)

# Compare specific runs
df = compare_backtest_runs([1, 2, 3])
print(df[["run_name", "total_trades", "win_rate_pct", "total_pnl", "sharpe_ratio"]])
```

- [ ] Run multiple backtests with different parameters
- [ ] Compare results using `compare_backtest_runs()`
- [ ] Identify best-performing strategy

## Advanced (Optional)

- [ ] Query by date range:
  ```python
  df = query_time_series("SPY", "1min", start_date="2023-01-01", end_date="2023-06-30")
  ```

- [ ] Resample timeframes:
  ```python
  from db.query import resample_time_series
  df = resample_time_series("SPY", "1min", "5min")
  ```

- [ ] Export results:
  ```python
  from db.backtest_store import export_backtest_to_json, export_trades_to_csv
  export_backtest_to_json(run_id=1, output_path="results/run1.json")
  export_trades_to_csv(run_id=1, output_path="results/run1_trades.csv")
  ```

- [ ] View historical runs from CLI:
  ```bash
  python -m db.backtest_store list
  python -m db.backtest_store load 1
  python -m db.backtest_store compare 1 2 3
  ```

## Verify Everything Works

Run the complete example:

```bash
python example_tier0.py
```

Expected output:
- ✅ Example 1: CSV → Tier 0 Ingestion
- ✅ Example 2: Query & Backtest
- ✅ Example 3: Save Backtest Result
- ✅ Example 4: Compare Backtest Runs
- ✅ All examples complete!

---

## 🎯 Success Criteria

You're successfully using Tier 0 when:

- [x] Database initialized (`data/tier0.db` exists)
- [ ] At least one dataset ingested (check with `ingest_data.py list`)
- [ ] Queries return data faster than CSV loading
- [ ] Backtest results are being saved automatically
- [ ] You can compare runs with `compare_backtest_runs()`

---

## 📊 Performance Check

Before:
```python
import time
start = time.time()
df = pd.read_csv("data/SPY.csv")
print(f"CSV load time: {time.time() - start:.2f}s")
```

After:
```python
import time
start = time.time()
df = query_time_series("SPY", "1min")
print(f"Parquet load time: {time.time() - start:.2f}s")
```

Expected: **10-100x faster** (e.g., 2.5s → 0.05s)

---

## 🆘 Need Help?

| Issue | Solution |
|-------|----------|
| "No datasets found" | Run `python ingest_data.py list` to check |
| DuckDB import error | Run `pip install -r requirements.txt` |
| Slow queries | Check file sizes, use date filters |
| Can't find dataset_id | Run `from db.schema import get_datasets; print(get_datasets(conn))` |

---

## 📖 Documentation

- **Quick Start:** [TIER0_QUICKSTART.md](TIER0_QUICKSTART.md)
- **Complete Guide:** [TIER0_README.md](TIER0_README.md)
- **Summary:** [TIER0_SUMMARY.md](TIER0_SUMMARY.md)
- **Examples:** [example_tier0.py](example_tier0.py)

---

## 🎉 You're Ready!

Once you've completed this checklist, you have:
- ✅ Production-ready database layer
- ✅ 10-100x faster data loading
- ✅ Automatic backtest tracking
- ✅ Easy strategy comparison
- ✅ $0/month cost

Start backtesting! 🚀
