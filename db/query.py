"""
DuckDB-powered query interface for Parquet time-series data.
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from db.schema import get_connection, get_datasets


def query_time_series(
    symbol: str,
    timeframe: str = "1min",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    columns: Optional[List[str]] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Query time-series data from Parquet using DuckDB.
    
    Args:
        symbol: Ticker symbol (e.g., "SPY")
        timeframe: Timeframe (e.g., "1min", "5min")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        columns: Columns to select (None = all)
    
    Returns:
        DataFrame with OHLCV data
    """
    
    # Get parquet file paths from SQLite
    conn = get_connection(db_path)
    datasets = get_datasets(conn, symbol=symbol, timeframe=timeframe)
    conn.close()
    
    if not datasets:
        raise ValueError(f"No datasets found for {symbol} @ {timeframe}")
    
    # Filter by date range if specified
    if start_date or end_date:
        filtered = []
        for ds in datasets:
            ds_start = ds["start_date"]
            ds_end = ds["end_date"]
            
            # Check if dataset overlaps with requested range
            if start_date and ds_end < start_date:
                continue
            if end_date and ds_start > end_date:
                continue
            
            filtered.append(ds)
        
        datasets = filtered
    
    if not datasets:
        raise ValueError(f"No datasets found in date range: {start_date} → {end_date}")
    
    # Build DuckDB query
    file_paths = [ds["file_path"] for ds in datasets]
    
    # Column selection
    col_str = ", ".join(columns) if columns else "*"
    
    # Build UNION query for multiple files
    queries = []
    for path in file_paths:
        query = f"SELECT {col_str} FROM read_parquet('{path}')"
        
        # Add date filters
        if start_date:
            query += f" WHERE timestamp >= '{start_date}'"
        if end_date:
            if start_date:
                query += f" AND timestamp <= '{end_date}'"
            else:
                query += f" WHERE timestamp <= '{end_date}'"
        
        queries.append(query)
    
    full_query = " UNION ALL ".join(queries)
    full_query += " ORDER BY timestamp"
    
    # Execute with DuckDB
    print(f"🔍 Querying {len(file_paths)} parquet file(s) for {symbol}...")
    df = duckdb.query(full_query).to_df()
    
    print(f"✅ Loaded {len(df):,} rows")
    
    return df


def query_latest(
    symbol: str,
    timeframe: str = "1min",
    limit: int = 1000,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """Get the most recent N rows for a symbol."""
    
    conn = get_connection(db_path)
    datasets = get_datasets(conn, symbol=symbol, timeframe=timeframe)
    conn.close()
    
    if not datasets:
        raise ValueError(f"No datasets found for {symbol} @ {timeframe}")
    
    # Get the most recent dataset
    latest_dataset = max(datasets, key=lambda d: d["end_date"])
    file_path = latest_dataset["file_path"]
    
    query = f"""
        SELECT * FROM read_parquet('{file_path}')
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    
    df = duckdb.query(query).to_df()
    
    # Reverse to chronological order
    df = df.iloc[::-1].reset_index(drop=True)
    
    return df


def query_date_range_summary(
    symbol: str,
    timeframe: str = "1min",
    start_date: str = None,
    end_date: str = None,
    db_path: Optional[Path] = None
) -> dict:
    """
    Get summary statistics for a date range without loading all data.
    Useful for quick validation.
    """
    
    conn = get_connection(db_path)
    datasets = get_datasets(conn, symbol=symbol, timeframe=timeframe)
    conn.close()
    
    if not datasets:
        raise ValueError(f"No datasets found for {symbol} @ {timeframe}")
    
    # Filter datasets
    if start_date or end_date:
        filtered = []
        for ds in datasets:
            if start_date and ds["end_date"] < start_date:
                continue
            if end_date and ds["start_date"] > end_date:
                continue
            filtered.append(ds)
        datasets = filtered
    
    if not datasets:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "row_count": 0,
            "datasets": 0,
            "start_date": None,
            "end_date": None
        }
    
    # Compute aggregates
    total_rows = sum(ds["row_count"] for ds in datasets)
    min_date = min(ds["start_date"] for ds in datasets)
    max_date = max(ds["end_date"] for ds in datasets)
    total_size = sum(ds["file_size_bytes"] for ds in datasets)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "row_count": total_rows,
        "datasets": len(datasets),
        "start_date": min_date,
        "end_date": max_date,
        "total_size_mb": round(total_size / 1024 / 1024, 2)
    }


def resample_time_series(
    symbol: str,
    source_timeframe: str,
    target_timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Resample time-series to different timeframe using DuckDB.
    
    Example: Resample 1min → 5min
    """
    
    # Load source data
    df = query_time_series(
        symbol=symbol,
        timeframe=source_timeframe,
        start_date=start_date,
        end_date=end_date,
        db_path=db_path
    )
    
    if df.empty:
        return df
    
    # Map target timeframe to pandas resample rule
    timeframe_map = {
        "1min": "1T",
        "5min": "5T",
        "15min": "15T",
        "1h": "1H",
        "1d": "1D"
    }
    
    rule = timeframe_map.get(target_timeframe)
    if not rule:
        raise ValueError(f"Unsupported target timeframe: {target_timeframe}")
    
    # Set timestamp as index
    df = df.set_index("timestamp")
    
    # Resample OHLCV data
    resampled = df.resample(rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    
    resampled = resampled.reset_index()
    
    print(f"✅ Resampled {len(df):,} → {len(resampled):,} rows ({source_timeframe} → {target_timeframe})")
    
    return resampled


def query_all_symbols(db_path: Optional[Path] = None) -> pd.DataFrame:
    """List all available symbols with dataset counts."""
    
    conn = get_connection(db_path)
    
    query = """
        SELECT 
            s.symbol,
            s.asset_type,
            s.vendor,
            COUNT(DISTINCT d.dataset_id) as dataset_count,
            COUNT(DISTINCT d.timeframe) as timeframe_count,
            MIN(d.start_date) as earliest_date,
            MAX(d.end_date) as latest_date,
            SUM(d.row_count) as total_rows,
            ROUND(SUM(d.file_size_bytes) / 1024.0 / 1024.0, 2) as total_size_mb
        FROM symbols s
        LEFT JOIN datasets d ON s.symbol_id = d.symbol_id
        GROUP BY s.symbol, s.asset_type, s.vendor
        ORDER BY s.symbol
    """
    
    cursor = conn.execute(query)
    df = pd.DataFrame([dict(row) for row in cursor.fetchall()])
    conn.close()
    
    return df


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m db.query <symbol> [timeframe]")
        print("\nExamples:")
        print("  python -m db.query SPY 1min")
        print("  python -m db.query --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        df = query_all_symbols()
        print("\n📊 Available Symbols:\n")
        print(df.to_string(index=False))
        sys.exit(0)
    
    symbol = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1min"
    
    # Get summary
    summary = query_date_range_summary(symbol, timeframe)
    print(f"\n📈 {symbol} @ {timeframe}")
    print(f"   Rows: {summary['row_count']:,}")
    print(f"   Date Range: {summary['start_date']} → {summary['end_date']}")
    print(f"   Size: {summary['total_size_mb']} MB")
    
    # Load first 10 rows
    print(f"\n🔍 First 10 rows:")
    df = query_time_series(symbol, timeframe)
    print(df.head(10).to_string(index=False))
