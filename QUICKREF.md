# Quick Reference - Iron Condor Backtester v2.0

## 🚀 Quick Start
```bash
streamlit run app.py
```

## 📂 File Structure
```
app.py           → Main entry point
config.py        → Constants & settings
core/            → Business logic (io, indicators, backtest, metrics)
ui/              → UI components (layout, charts, exports)
tests/           → Test suite
```

## 🎯 Workflow

1. **Upload Data** (Tab 1)
   - CSV: timestamp, open, high, low, close, vwap
   - TXT: One date per line (YYYY-MM-DD)

2. **Configure** (Tab 2)
   - Select timeframe
   - Set HV range
   - Configure exits
   - Optional: Enable trend bias

3. **Run** (Tab 2)
   - Click "▶️ Run Backtest"
   - Wait for progress bar

4. **Analyze** (Tab 3-6)
   - Results: Summary + charts
   - Trades: Full history
   - Rejections: Filter diagnostics
   - Diagnostics: Price chart

## ⚙️ Key Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| HV Min | 15.0 | 0-200 | Minimum volatility for entry (%) |
| HV Max | 40.0 | 0-200 | Maximum volatility for entry (%) |
| ADX Exit | 30 | 10-100 | Exit when trend emerges |
| VWAP K | 1.0 | 0-5 | VWAP exit sensitivity |
| Bias Strength | 2.0 | 0-20 | Strike adjustment ($) |
| Wing Extension | 20.0 | 0-100 | Wing width increase (%) |
| Days Before | 7 | 0-30 | Blackout before event |
| Days After | 1 | 0-30 | Blackout after event |

## 📊 Key Metrics

**Performance:**
- Total P&L
- Win Rate (%)
- Profit Factor
- Return on Risk (%)

**Risk:**
- Max Drawdown ($)
- Max Drawdown (%)
- Avg Risk per Trade
- Worst Loss

**Trade Stats:**
- Total Trades
- Wins / Losses
- Avg Win / Loss
- Win Streak / Loss Streak

## 🔧 Common Tasks

### Clear Cache
```
Sidebar → 🗑️ Clear Cache
```

### Export Trades
```
Trades Tab → 📥 Download Trades CSV
```

### Export Run Config
```
Diagnostics Tab → 📥 Download Config JSON
```

### Change Theme
```
Edit config.py → THEME_COLORS dictionary
```

### Run Tests
```bash
pytest tests/ -v
```

### Benchmark Performance
```bash
python benchmark.py
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Import Error | `cd` to project directory |
| Module Not Found | `pip install -r requirements.txt` |
| Slow Performance | Clear cache, reduce data size |
| Different Results | Verify same parameters & timeframe |

## 📚 Documentation Files

- `README.md` - Full user guide
- `SUMMARY.md` - Technical overview
- `REFACTOR_PLAN.md` - Architecture details
- `MIGRATION.md` - v1.0 → v2.0 guide

## 💡 Tips

✅ Start with Daily timeframe for faster execution
✅ Use smaller date ranges for initial tests
✅ Export configuration after successful runs
✅ Clear cache if results seem cached
✅ Check validation warnings before running

## 🎨 Theme Colors

```python
primary: "#00FF41"    # Matrix green
secondary: "#00D9FF"  # Cyan
warning: "#FFB800"    # Amber
error: "#FF4B4B"      # Red
```

## 📈 Performance Expectations

| Data Size | Time | Memory |
|-----------|------|--------|
| 1K rows | <1s | ~50 MB |
| 10K rows | ~2s | ~100 MB |
| 100K rows | ~8s | ~300 MB |
| 1M rows | ~75s | ~1.5 GB |

## 🔑 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| R | Rerun app |
| C | Clear cache (while focused on button) |
| Tab | Navigate between tabs |

## 🆘 Getting Help

1. Check `README.md`
2. Review `SUMMARY.md`
3. Run tests: `pytest tests/ -v`
4. Check validation warnings
5. Open GitHub issue

---

**Version:** 2.0.0 | **Updated:** 2026-01-12
