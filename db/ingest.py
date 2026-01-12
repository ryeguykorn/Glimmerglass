"""
Data ingestion pipeline: CSV → Parquet + SQLite metadata
"""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, Tuple
import hashlib
from datetime import datetime

from db.schema import get_connection, add_symbol, add_dataset


def compute_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def ingest_csv_to_parquet(
    csv_path: Path,
    symbol: str,
    timeframe: str = "1min",
    asset_type: str = "equity",
    vendor: str = "csv_import",
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None
) -> Tuple[Path, int]:
    """
    Load CSV, write Parquet, register in SQLite.
    
    Returns:
        (parquet_path, dataset_id)
    """
    
    # Set output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "parquet"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load CSV
    print(f"📂 Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Validate required columns
    required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Parse timestamp
    if df["timestamp"].dtype == "object":
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Sort by timestamp (critical for Parquet performance)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Get date range
    start_date = df["timestamp"].min().strftime("%Y-%m-%d")
    end_date = df["timestamp"].max().strftime("%Y-%m-%d")
    row_count = len(df)
    
    print(f"📊 {row_count:,} rows | {start_date} → {end_date}")
    
    # Create output path: symbol_timeframe_startdate_enddate.parquet
    safe_symbol = symbol.replace("/", "_").replace(":", "_")
    filename = f"{safe_symbol}_{timeframe}_{start_date}_{end_date}.parquet"
    parquet_path = output_dir / filename
    
    # Write Parquet with compression
    print(f"💾 Writing Parquet: {parquet_path}")
    table = pa.Table.from_pandas(df)
    pq.write_table(
        table,
        parquet_path,
        compression="zstd",
        compression_level=3,
        use_dictionary=True,
        write_statistics=True
    )
    
    file_size = parquet_path.stat().st_size
    checksum = compute_checksum(parquet_path)
    
    print(f"✅ Parquet written: {file_size / 1024 / 1024:.2f} MB")
    
    # Register in database
    conn = get_connection(db_path)
    
    # Add symbol
    symbol_id = add_symbol(conn, symbol, asset_type, vendor, description=None)
    
    # Add dataset
    dataset_id = add_dataset(
        conn,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        row_count=row_count,
        file_path=str(parquet_path),
        file_size=file_size,
        checksum=checksum
    )
    
    conn.close()
    
    print(f"🎯 Registered as dataset_id={dataset_id}")
    
    return parquet_path, dataset_id


def ingest_dataframe(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str = "1min",
    asset_type: str = "equity",
    vendor: str = "manual",
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None
) -> Tuple[Path, int]:
    """
    Ingest an in-memory DataFrame directly to Parquet.
    Useful for programmatic data loading or API imports.
    """
    
    # Validate
    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must have 'timestamp' column")
    
    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Set output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "parquet"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get date range
    start_date = df["timestamp"].min().strftime("%Y-%m-%d")
    end_date = df["timestamp"].max().strftime("%Y-%m-%d")
    row_count = len(df)
    
    # Create output path
    safe_symbol = symbol.replace("/", "_").replace(":", "_")
    filename = f"{safe_symbol}_{timeframe}_{start_date}_{end_date}.parquet"
    parquet_path = output_dir / filename
    
    # Write Parquet
    table = pa.Table.from_pandas(df)
    pq.write_table(
        table,
        parquet_path,
        compression="zstd",
        compression_level=3,
        use_dictionary=True,
        write_statistics=True
    )
    
    file_size = parquet_path.stat().st_size
    checksum = compute_checksum(parquet_path)
    
    # Register in database
    conn = get_connection(db_path)
    symbol_id = add_symbol(conn, symbol, asset_type, vendor)
    dataset_id = add_dataset(
        conn,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        row_count=row_count,
        file_path=str(parquet_path),
        file_size=file_size,
        checksum=checksum
    )
    conn.close()
    
    print(f"✅ Ingested {row_count:,} rows → dataset_id={dataset_id}")
    
    return parquet_path, dataset_id


def bulk_ingest_directory(
    csv_dir: Path,
    symbol_pattern: str = "*",
    timeframe: str = "1min",
    asset_type: str = "equity",
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None
) -> list:
    """
    Ingest all CSV files in a directory.
    
    Args:
        csv_dir: Directory containing CSV files
        symbol_pattern: Glob pattern for CSV filenames (e.g., "SPY_*.csv")
        timeframe: Timeframe for all files
        asset_type: Asset type for all files
    
    Returns:
        List of (parquet_path, dataset_id) tuples
    """
    csv_files = list(csv_dir.glob(f"{symbol_pattern}.csv"))
    
    if not csv_files:
        print(f"⚠️  No CSV files found in {csv_dir}")
        return []
    
    print(f"📦 Found {len(csv_files)} CSV files to ingest")
    
    results = []
    for csv_file in csv_files:
        # Extract symbol from filename (e.g., "SPY_1min.csv" → "SPY")
        symbol = csv_file.stem.split("_")[0]
        
        try:
            result = ingest_csv_to_parquet(
                csv_file,
                symbol=symbol,
                timeframe=timeframe,
                asset_type=asset_type,
                output_dir=output_dir,
                db_path=db_path
            )
            results.append(result)
        except Exception as e:
            print(f"❌ Failed to ingest {csv_file}: {e}")
            continue
    
    print(f"\n✅ Successfully ingested {len(results)}/{len(csv_files)} files")
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m db.ingest <csv_path> <symbol> [timeframe]")
        print("Example: python -m db.ingest data/SPY.csv SPY 1min")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    symbol = sys.argv[2]
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "1min"
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    parquet_path, dataset_id = ingest_csv_to_parquet(
        csv_path,
        symbol=symbol,
        timeframe=timeframe
    )
    
    print(f"\n🎉 Done! Dataset ID: {dataset_id}")
