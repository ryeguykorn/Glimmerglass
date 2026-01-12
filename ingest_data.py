#!/usr/bin/env python3
"""
Tier 0 Data Ingestion CLI Tool

Simple command-line interface for loading CSV data into Parquet + SQLite.
"""
import argparse
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from db.schema import get_connection, init_database, get_datasets
from db.ingest import ingest_csv_to_parquet, bulk_ingest_directory
from db.query import query_all_symbols, query_date_range_summary


def cmd_init(args):
    """Initialize the Tier 0 database."""
    db_path = Path(args.db) if args.db else None
    conn = get_connection(db_path)
    init_database(conn)
    conn.close()
    
    print("✅ Tier 0 database initialized")
    if db_path:
        print(f"   Location: {db_path}")
    else:
        from db.schema import DEFAULT_DB_PATH
        print(f"   Location: {DEFAULT_DB_PATH}")


def cmd_ingest(args):
    """Ingest a single CSV file."""
    csv_path = Path(args.csv)
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    output_dir = Path(args.output) if args.output else None
    db_path = Path(args.db) if args.db else None
    
    parquet_path, dataset_id = ingest_csv_to_parquet(
        csv_path=csv_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        asset_type=args.asset_type,
        vendor=args.vendor,
        output_dir=output_dir,
        db_path=db_path
    )
    
    print(f"\n🎉 Success!")
    print(f"   Parquet: {parquet_path}")
    print(f"   Dataset ID: {dataset_id}")


def cmd_bulk_ingest(args):
    """Ingest all CSV files in a directory."""
    csv_dir = Path(args.directory)
    
    if not csv_dir.exists():
        print(f"❌ Directory not found: {csv_dir}")
        sys.exit(1)
    
    output_dir = Path(args.output) if args.output else None
    db_path = Path(args.db) if args.db else None
    
    results = bulk_ingest_directory(
        csv_dir=csv_dir,
        symbol_pattern=args.pattern,
        timeframe=args.timeframe,
        asset_type=args.asset_type,
        output_dir=output_dir,
        db_path=db_path
    )
    
    print(f"\n🎉 Bulk ingestion complete!")
    print(f"   Successfully ingested: {len(results)} files")


def cmd_list(args):
    """List all symbols and datasets."""
    db_path = Path(args.db) if args.db else None
    
    if args.datasets:
        # List datasets for a specific symbol
        conn = get_connection(db_path)
        datasets = get_datasets(conn, symbol=args.symbol, timeframe=args.timeframe)
        conn.close()
        
        if not datasets:
            print(f"⚠️  No datasets found")
            return
        
        print(f"\n📊 Datasets{' for ' + args.symbol if args.symbol else ''}:\n")
        for ds in datasets:
            print(f"  #{ds['dataset_id']}: {ds['symbol']} @ {ds['timeframe']}")
            print(f"     {ds['start_date']} → {ds['end_date']} ({ds['row_count']:,} rows)")
            print(f"     {ds['file_path']}")
            print()
    else:
        # List all symbols
        df = query_all_symbols(db_path)
        
        if df.empty:
            print("⚠️  No symbols found. Use 'ingest' to add data.")
            return
        
        print("\n📊 Available Symbols:\n")
        print(df.to_string(index=False))


def cmd_info(args):
    """Show summary info for a symbol."""
    db_path = Path(args.db) if args.db else None
    
    summary = query_date_range_summary(
        symbol=args.symbol,
        timeframe=args.timeframe,
        db_path=db_path
    )
    
    print(f"\n📈 {args.symbol} @ {args.timeframe}")
    print(f"   Rows: {summary['row_count']:,}")
    print(f"   Datasets: {summary['datasets']}")
    print(f"   Date Range: {summary['start_date']} → {summary['end_date']}")
    print(f"   Total Size: {summary['total_size_mb']} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Tier 0 Data Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database
  ./ingest_data.py init

  # Ingest single CSV
  ./ingest_data.py ingest data/SPY.csv SPY --timeframe 1min

  # Bulk ingest all CSVs in directory
  ./ingest_data.py bulk data/csvs/ --pattern "*.csv"

  # List all symbols
  ./ingest_data.py list

  # List datasets for a symbol
  ./ingest_data.py list --datasets --symbol SPY

  # Show summary info
  ./ingest_data.py info SPY --timeframe 1min
        """
    )
    
    parser.add_argument(
        "--db",
        help="Path to SQLite database (default: data/tier0.db)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Init command
    parser_init = subparsers.add_parser("init", help="Initialize database")
    parser_init.set_defaults(func=cmd_init)
    
    # Ingest command
    parser_ingest = subparsers.add_parser("ingest", help="Ingest a CSV file")
    parser_ingest.add_argument("csv", help="Path to CSV file")
    parser_ingest.add_argument("symbol", help="Symbol ticker (e.g., SPY)")
    parser_ingest.add_argument("--timeframe", default="1min", help="Timeframe (default: 1min)")
    parser_ingest.add_argument("--asset-type", default="equity", help="Asset type (default: equity)")
    parser_ingest.add_argument("--vendor", default="csv_import", help="Data vendor (default: csv_import)")
    parser_ingest.add_argument("--output", help="Output directory for parquet files")
    parser_ingest.set_defaults(func=cmd_ingest)
    
    # Bulk ingest command
    parser_bulk = subparsers.add_parser("bulk", help="Bulk ingest CSV files from directory")
    parser_bulk.add_argument("directory", help="Directory containing CSV files")
    parser_bulk.add_argument("--pattern", default="*", help="Filename pattern (default: *)")
    parser_bulk.add_argument("--timeframe", default="1min", help="Timeframe for all files")
    parser_bulk.add_argument("--asset-type", default="equity", help="Asset type for all files")
    parser_bulk.add_argument("--output", help="Output directory for parquet files")
    parser_bulk.set_defaults(func=cmd_bulk_ingest)
    
    # List command
    parser_list = subparsers.add_parser("list", help="List symbols or datasets")
    parser_list.add_argument("--datasets", action="store_true", help="List datasets instead of symbols")
    parser_list.add_argument("--symbol", help="Filter by symbol")
    parser_list.add_argument("--timeframe", help="Filter by timeframe")
    parser_list.set_defaults(func=cmd_list)
    
    # Info command
    parser_info = subparsers.add_parser("info", help="Show summary info for a symbol")
    parser_info.add_argument("symbol", help="Symbol ticker")
    parser_info.add_argument("--timeframe", default="1min", help="Timeframe (default: 1min)")
    parser_info.set_defaults(func=cmd_info)
    
    # Parse and execute
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
