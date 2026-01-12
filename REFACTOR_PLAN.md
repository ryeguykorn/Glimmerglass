# Iron Condor Backtester - Refactoring Plan

## Executive Summary
Complete restructuring of monolithic 818-line Streamlit app into modular, performant, and maintainable codebase.

## 1. Architecture Changes

### Current State
- Single 818-line file with mixed concerns
- Inline computation and UI rendering
- Limited error handling
- No tests

### Target Structure
```
Glimmerglass.WebApp/
├── app.py                    # Streamlit entry point
├── core/
│   ├── __init__.py
│   ├── io.py                 # Data loading & validation
│   ├── resample.py           # Timeframe resampling
│   ├── indicators.py         # Technical indicators
│   ├── backtest.py          # Backtest engine
│   ├── metrics.py           # Performance metrics
│   └── types.py             # Dataclasses for positions
├── ui/
│   ├── __init__.py
│   ├── layout.py            # Layout components & theme
│   ├── charts.py            # Plotly chart generators
│   └── exports.py           # CSV/JSON export utilities
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_backtest.py
│   ├── test_metrics.py
│   └── fixtures/            # Test data
├── config.py                 # Constants & configuration
├── requirements.txt
├── .streamlit/config.toml
└── README.md
```

## 2. Performance Optimizations

### A. Backtest Loop (CRITICAL)
**Current Issues:**
- Dict-based position tracking
- Per-iteration progress updates
- Unnecessary DataFrame copies

**Solutions:**
- ✅ Use numpy arrays (already done)
- ✅ Vectorized blackout mask (already done)
- 🔄 **NEW**: Use `dataclass` for Position (memory efficient)
- 🔄 **NEW**: Pre-allocate equity/trades arrays
- 🔄 **NEW**: Batch progress updates (every 5%)

### B. Indicator Computation
**Current Issues:**
- Multiple rolling calculations on same window
- DataFrame copies in compute_trend_flags

**Solutions:**
- 🔄 In-place computation where possible
- 🔄 Shared rolling window objects
- 🔄 Numba JIT for custom indicators (optional)

### C. Caching Strategy
**Current:**
- Generic @st.cache_data
- No explicit cache management

**Solutions:**
- 🔄 Hash-based cache keys using file content hash
- 🔄 Clear cache button in UI
- 🔄 Separate caches for data/indicators/results

## 3. UI/UX Improvements

### A. Layout Restructuring
**NEW: Tab-Based Navigation**
```
Tab 1: 📊 Data
  - File uploads
  - Data preview
  - Validation status

Tab 2: ⚙️ Parameters  
  - Timeframe selection
  - Backtest settings (collapsible)
  - Trend bias settings (collapsible)
  - Run button

Tab 3: 📈 Results
  - Summary cards (5 key metrics)
  - Equity curve + drawdown overlay
  - P/L distribution histogram

Tab 4: 📋 Trades
  - Trades table with filters
  - Monthly breakdown
  - Export button

Tab 5: 🚫 Rejections
  - Filtered evaluations
  - Reason breakdown chips
  - Export button

Tab 6: 🔍 Diagnostics
  - Price chart with indicators
  - Entry/exit markers
  - Run configuration JSON
```

### B. Sidebar (NEW)
- Quick stats dashboard
- Parameter snapshot
- Clear cache button
- Export all data button

### C. Visual Theme
**Color Palette (Terminal Finance):**
- Background: `#0E1117` (darker)
- Primary: `#00FF41` (matrix green)
- Secondary: `#00D9FF` (cyan)
- Warning: `#FFB800` (amber)
- Error: `#FF4B4B` (red)
- Surface: `#1E2329` (card background)

**Typography:**
- Headers: `IBM Plex Mono`, bold
- Body: `Inter`, regular
- Mono: `JetBrains Mono`

## 4. Reliability Enhancements

### A. Input Validation
**CSV Schema Enforcement:**
```python
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "vwap"}
OPTIONAL_COLUMNS = {"volume"}
COLUMN_DTYPES = {
    "timestamp": "datetime64[ns]",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "vwap": "float64"
}
```

**Validation Checks:**
- ✅ Duplicate timestamps → dedupe + warn
- ✅ Missing values → interpolate or drop + warn
- ✅ Timezone awareness → convert to UTC
- ✅ Data integrity (high >= low, etc.)
- ✅ Min data requirement (e.g., 252 bars for indicators)

### B. Error Handling
- Try-catch blocks around file I/O
- Graceful degradation for indicator failures
- User-friendly error messages with recovery suggestions

### C. Deterministic Caching
**Cache Key Strategy:**
```python
def compute_cache_key(df, params):
    df_hash = hashlib.sha256(
        pd.util.hash_pandas_object(df).values
    ).hexdigest()[:16]
    param_hash = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode()
    ).hexdigest()[:16]
    return f"{df_hash}_{param_hash}"
```

## 5. Export Functionality

### A. CSV Exports
- **Trades**: All trade details
- **Equity Curve**: Timestamp + cash balance
- **Rejections**: Filtered evaluations with reasons

### B. Run Configuration JSON
```json
{
  "run_id": "uuid-v4",
  "timestamp": "2026-01-12T15:30:00Z",
  "data": {
    "rows": 10000,
    "timeframe": "5-minute",
    "start_date": "2024-01-01",
    "end_date": "2025-12-31"
  },
  "parameters": {
    "hv_min": 15.0,
    "hv_max": 40.0,
    "adx_exit": 30,
    "vwap_k": 1.0,
    "use_bias": true,
    "trend_method": "VWAP Slope",
    "bias_strength": 2.0,
    "wing_ext_pct": 20.0,
    "days_before": 7,
    "days_after": 1,
    "bb_window": 390
  },
  "results": {
    "total_trades": 150,
    "win_rate": 68.5,
    "total_pnl": 12345.67,
    "max_drawdown": -3456.78
  }
}
```

## 6. Testing Strategy

### A. Unit Tests
- `test_indicators.py`: Verify RSI, ADX, BB calculations
- `test_backtest.py`: Position logic, exits, P/L calc
- `test_metrics.py`: Win rate, drawdown, profit factor

### B. Integration Tests
- End-to-end backtest with synthetic data
- Edge cases: empty data, single trade, all rejections

### C. Performance Tests
- Benchmark: 10K, 100K, 1M rows
- Memory profiling with `memory_profiler`

## 7. Bug Fixes Identified

### BUG #1: Walrus Operator Typo (Line 766)
```python
# Current (TYPO):
if use_trend_biaS:=use_trend_bias:

# Fixed:
if use_trend_bias:
```

### BUG #2: Progress Bar Updates
**Issue**: Updates every iteration → slow UI
**Fix**: Update every 5% (already partially done with `update_every`)

### BUG #3: Memory Cleanup
**Issue**: Large arrays not freed until GC
**Fix**: Explicit `del` + `gc.collect()` (already added)

## 8. Implementation Order

1. ✅ Create folder structure
2. ✅ Extract constants → `config.py`
3. ✅ Core modules (io, indicators, backtest, metrics)
4. ✅ Type definitions → `core/types.py`
5. ✅ UI modules (layout, charts, exports)
6. ✅ Main `app.py` with tabs
7. ✅ Tests
8. ✅ Documentation
9. ✅ Benchmark comparison

## 9. Performance Targets

| Metric | Before | Target | Method |
|--------|--------|--------|--------|
| 100K rows | ~15s | <5s | Numpy arrays, dataclasses |
| 1M rows | ~180s | <30s | Pre-allocation, batch updates |
| Memory (1M) | ~2GB | <800MB | Cleanup, efficient types |
| Cache hit | N/A | <100ms | Hash-based keying |

## 10. Non-Goals

- ❌ Machine learning / optimization
- ❌ Real-time data feeds
- ❌ Multi-threading (Streamlit limitation)
- ❌ Database persistence
- ❌ Custom indicators beyond current set
