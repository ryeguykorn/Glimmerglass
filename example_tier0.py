"""
Example: Integrate Tier 0 with existing backtester
"""
from pathlib import Path
import pandas as pd

# Import existing core modules
from core.io import load_csv_data
from core.backtest import run_backtest

# Import new Tier 0 modules
from db.ingest import ingest_dataframe
from db.query import query_time_series, query_date_range_summary
from db.backtest_store import save_backtest_result, list_recent_runs


def example_csv_to_tier0():
    """
    Example 1: Convert existing CSV workflow to Tier 0
    """
    print("=" * 60)
    print("Example 1: CSV → Tier 0 Ingestion")
    print("=" * 60)
    
    # Simulate loading a CSV (using your existing function)
    # df = load_csv_data("data/SPY.csv")
    
    # For demo, create sample data
    df = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=1000, freq="1T"),
        "open": [100.0 + i*0.01 for i in range(1000)],
        "high": [101.0 + i*0.01 for i in range(1000)],
        "low": [99.0 + i*0.01 for i in range(1000)],
        "close": [100.5 + i*0.01 for i in range(1000)],
        "volume": [10000] * 1000,
        "vwap": [100.25 + i*0.01 for i in range(1000)]
    })
    
    print(f"📊 Sample data: {len(df)} rows")
    
    # Ingest to Tier 0
    parquet_path, dataset_id = ingest_dataframe(
        df=df,
        symbol="SPY",
        timeframe="1min",
        asset_type="equity",
        vendor="example"
    )
    
    print(f"✅ Ingested as dataset_id={dataset_id}")
    print(f"   Parquet: {parquet_path}")
    
    return dataset_id


def example_query_and_backtest(dataset_id: int):
    """
    Example 2: Query data and run backtest
    """
    print("\n" + "=" * 60)
    print("Example 2: Query & Backtest")
    print("=" * 60)
    
    # Get summary first
    summary = query_date_range_summary("SPY", "1min")
    print(f"📈 SPY @ 1min")
    print(f"   Rows: {summary['row_count']:,}")
    print(f"   Date Range: {summary['start_date']} → {summary['end_date']}")
    print(f"   Size: {summary['total_size_mb']} MB")
    
    # Query data (fast!)
    df = query_time_series("SPY", "1min")
    print(f"\n✅ Loaded {len(df):,} rows from Parquet")
    
    # NOTE: Can't run actual backtest without full data/config,
    # but this shows the workflow
    print("\n💡 Next step: Run backtest with this data")
    print("   result = run_backtest(df, ...)")
    print("   run_id = save_backtest_result(result, dataset_id, config)")
    
    return df


def example_save_backtest():
    """
    Example 3: Save a backtest result (simulated)
    """
    print("\n" + "=" * 60)
    print("Example 3: Save Backtest Result")
    print("=" * 60)
    
    # Simulate a backtest result
    # In real usage, this comes from run_backtest()
    from core.types import BacktestResult
    from datetime import datetime, timedelta
    import pandas as pd
    
    # Create dummy trade data (matching actual backtest output format)
    trades_data = []
    for i in range(5):
        entry = datetime(2023, 1, 1) + timedelta(days=i*10)
        exit = entry + timedelta(days=7)
        
        trade = {
            "entry_date": entry,
            "exit_date": exit,
            "days_held": 7,
            "pnl": 150.0 + i*10,
            "pnl_pct": 1.5 + i*0.1,
            "status": "closed",
            "entry_reason": "BB_VWAP_RSI",
            "exit_reason": "MAX_PROFIT",
            "strike_width": 5.0,
            "distance": 10.0,
            "iv_rank": 0.6
        }
        trades_data.append(trade)
    
    trades_df = pd.DataFrame(trades_data)
    
    # Create a minimal BacktestResult
    # NOTE: We're creating a simplified version since the real one requires full data
    result_dict = {
        "trades": trades_df,
        "total_trades": len(trades_df),
        "win_rate": 0.8,
        "total_pnl": trades_df["pnl"].sum(),
        "avg_pnl": trades_df["pnl"].mean(),
        "sharpe_ratio": 1.234,
        "max_drawdown": -0.05
    }
    
    # Save to database (using dict instead of BacktestResult object)
    from db.schema import get_connection, add_backtest_run
    import json
    
    config = {
        "bb_window": 20,
        "rsi_window": 14,
        "adx_threshold": 25,
        "max_trades": 5
    }
    
    conn = get_connection()
    
    run_id = add_backtest_run(
        conn,
        dataset_id=1,
        config=config,
        start_date="2023-01-01",
        end_date="2023-12-31",
        metrics={
            "total_trades": result_dict["total_trades"],
            "win_rate": result_dict["win_rate"],
            "avg_pnl": result_dict["avg_pnl"],
            "total_pnl": result_dict["total_pnl"],
            "sharpe_ratio": result_dict["sharpe_ratio"],
            "max_drawdown": result_dict["max_drawdown"]
        },
        runtime=1.234,
        run_name="Example Strategy - SPY 2023"
    )
    
    # Save trades
    from db.schema import add_trades
    add_trades(conn, run_id, trades_data)
    
    conn.close()
    
    print(f"\n✅ Saved as run_id={run_id}")
    print(f"   Total trades: {len(trades_data)}")
    print(f"   Total PnL: ${result_dict['total_pnl']:.2f}")
    
    return run_id


def example_compare_runs():
    """
    Example 4: List and compare backtest runs
    """
    print("\n" + "=" * 60)
    print("Example 4: Compare Backtest Runs")
    print("=" * 60)
    
    # List recent runs
    df = list_recent_runs(limit=10)
    
    if df.empty:
        print("⚠️  No backtest runs found yet")
        return
    
    print("\n📊 Recent Backtest Runs:\n")
    print(df.to_string(index=False))


def main():
    """
    Run all examples to demonstrate Tier 0 workflow
    """
    print("\n🚀 Tier 0 Integration Examples\n")
    
    # Example 1: Ingest data
    dataset_id = example_csv_to_tier0()
    
    # Example 2: Query data
    df = example_query_and_backtest(dataset_id)
    
    # Example 3: Save backtest
    run_id = example_save_backtest()
    
    # Example 4: Compare runs
    example_compare_runs()
    
    print("\n" + "=" * 60)
    print("✅ All examples complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Ingest your real CSV data: ./ingest_data.py ingest data/SPY.csv SPY")
    print("   2. Update app.py to use query_time_series() instead of CSV loading")
    print("   3. Save backtest results with save_backtest_result()")
    print("   4. Compare strategies with compare_backtest_runs()")
    print("\n📖 See TIER0_README.md for full documentation")


if __name__ == "__main__":
    main()
