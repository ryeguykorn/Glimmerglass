"""
Backtest result storage and retrieval.
"""
import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import time

from db.schema import get_connection, add_backtest_run, add_trades, get_backtest_runs
from core.types import BacktestResult


def save_backtest_result(
    result: BacktestResult,
    dataset_id: int,
    config: dict,
    run_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> int:
    """
    Save a complete BacktestResult to the database.
    
    Args:
        result: BacktestResult object from core.backtest
        dataset_id: Dataset ID from datasets table
        config: Dictionary of backtest parameters
        run_name: Optional name for this run
    
    Returns:
        run_id
    """
    
    # Extract metrics
    metrics = {
        "total_trades": len(result.trades),
        "win_rate": None,
        "avg_pnl": None,
        "total_pnl": None,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown
    }
    
    if result.trades:
        wins = sum(1 for t in result.trades if t.pnl > 0)
        metrics["win_rate"] = wins / len(result.trades) if result.trades else None
        metrics["avg_pnl"] = sum(t.pnl for t in result.trades) / len(result.trades)
        metrics["total_pnl"] = sum(t.pnl for t in result.trades)
    
    # Get date range from trades
    if result.trades:
        start_date = min(t.entry_date for t in result.trades).strftime("%Y-%m-%d")
        end_date = max(t.exit_date for t in result.trades).strftime("%Y-%m-%d")
    else:
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = start_date
    
    # Save backtest run metadata
    conn = get_connection(db_path)
    
    run_id = add_backtest_run(
        conn,
        dataset_id=dataset_id,
        config=config,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        runtime=0.0,  # Can be set by caller if desired
        run_name=run_name
    )
    
    # Convert Position objects to trade dictionaries
    trades_data = []
    for pos in result.trades:
        trade = {
            "entry_date": pos.entry_date.strftime("%Y-%m-%d"),
            "exit_date": pos.exit_date.strftime("%Y-%m-%d") if pos.exit_date else None,
            "days_held": pos.days_held,
            "pnl": pos.pnl,
            "pnl_pct": pos.pnl_pct,
            "status": pos.status,
            "entry_reason": pos.entry_reason,
            "exit_reason": pos.exit_reason,
            "strike_width": pos.strike_width,
            "distance_from_price": pos.distance,
            "iv_rank": pos.iv_rank
        }
        trades_data.append(trade)
    
    # Bulk insert trades
    if trades_data:
        add_trades(conn, run_id, trades_data)
    
    conn.close()
    
    print(f"✅ Saved backtest run_id={run_id} with {len(trades_data)} trades")
    
    return run_id


def load_backtest_result(
    run_id: int,
    db_path: Optional[Path] = None
) -> Dict:
    """
    Load a complete backtest result by run_id.
    
    Returns:
        Dictionary with run metadata, config, and trades
    """
    
    conn = get_connection(db_path)
    
    # Get run metadata
    cursor = conn.execute(
        """
        SELECT br.*, d.file_path, s.symbol, d.timeframe
        FROM backtest_runs br
        JOIN datasets d ON br.dataset_id = d.dataset_id
        JOIN symbols s ON d.symbol_id = s.symbol_id
        WHERE br.run_id = ?
        """,
        (run_id,)
    )
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Backtest run_id={run_id} not found")
    
    run_data = dict(row)
    
    # Parse config JSON
    run_data["config"] = json.loads(run_data["config_json"])
    del run_data["config_json"]
    
    # Get trades
    cursor = conn.execute(
        """
        SELECT * FROM trades
        WHERE run_id = ?
        ORDER BY entry_date
        """,
        (run_id,)
    )
    
    trades = [dict(row) for row in cursor.fetchall()]
    run_data["trades"] = trades
    
    conn.close()
    
    return run_data


def compare_backtest_runs(
    run_ids: List[int],
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Compare multiple backtest runs side-by-side.
    
    Returns:
        DataFrame with one row per run
    """
    
    conn = get_connection(db_path)
    
    placeholders = ",".join("?" * len(run_ids))
    query = f"""
        SELECT 
            br.run_id,
            br.run_name,
            s.symbol,
            d.timeframe,
            br.start_date,
            br.end_date,
            br.total_trades,
            ROUND(br.win_rate * 100, 2) as win_rate_pct,
            ROUND(br.avg_pnl, 2) as avg_pnl,
            ROUND(br.total_pnl, 2) as total_pnl,
            ROUND(br.sharpe_ratio, 3) as sharpe_ratio,
            ROUND(br.max_drawdown * 100, 2) as max_drawdown_pct,
            ROUND(br.runtime_seconds, 2) as runtime_sec,
            br.created_at
        FROM backtest_runs br
        JOIN datasets d ON br.dataset_id = d.dataset_id
        JOIN symbols s ON d.symbol_id = s.symbol_id
        WHERE br.run_id IN ({placeholders})
        ORDER BY br.created_at DESC
    """
    
    cursor = conn.execute(query, run_ids)
    df = pd.DataFrame([dict(row) for row in cursor.fetchall()])
    conn.close()
    
    return df


def list_recent_runs(
    limit: int = 20,
    symbol: Optional[str] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    List recent backtest runs with summary metrics.
    """
    
    conn = get_connection(db_path)
    
    query = """
        SELECT 
            br.run_id,
            br.run_name,
            s.symbol,
            d.timeframe,
            br.start_date,
            br.end_date,
            br.total_trades,
            ROUND(br.win_rate * 100, 2) as win_rate_pct,
            ROUND(br.total_pnl, 2) as total_pnl,
            ROUND(br.sharpe_ratio, 3) as sharpe,
            br.created_at
        FROM backtest_runs br
        JOIN datasets d ON br.dataset_id = d.dataset_id
        JOIN symbols s ON d.symbol_id = s.symbol_id
        WHERE 1=1
    """
    
    params = []
    if symbol:
        query += " AND s.symbol = ?"
        params.append(symbol)
    
    query += " ORDER BY br.created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    df = pd.DataFrame([dict(row) for row in cursor.fetchall()])
    conn.close()
    
    return df


def export_backtest_to_json(
    run_id: int,
    output_path: Path,
    db_path: Optional[Path] = None
) -> None:
    """Export backtest result to JSON file."""
    
    data = load_backtest_result(run_id, db_path)
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"✅ Exported run_id={run_id} to {output_path}")


def export_trades_to_csv(
    run_id: int,
    output_path: Path,
    db_path: Optional[Path] = None
) -> None:
    """Export trades from a backtest run to CSV."""
    
    data = load_backtest_result(run_id, db_path)
    
    if not data["trades"]:
        print(f"⚠️  No trades found for run_id={run_id}")
        return
    
    df = pd.DataFrame(data["trades"])
    df.to_csv(output_path, index=False)
    
    print(f"✅ Exported {len(df)} trades to {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m db.backtest_store <command> [args]")
        print("\nCommands:")
        print("  list               - List recent backtest runs")
        print("  load <run_id>      - Load backtest result")
        print("  compare <id1> <id2> ... - Compare multiple runs")
        print("  export <run_id> <path>  - Export to JSON")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        df = list_recent_runs(limit=20)
        print("\n📊 Recent Backtest Runs:\n")
        print(df.to_string(index=False))
    
    elif command == "load":
        if len(sys.argv) < 3:
            print("Error: run_id required")
            sys.exit(1)
        
        run_id = int(sys.argv[2])
        data = load_backtest_result(run_id)
        
        print(f"\n📈 Backtest Run #{run_id}")
        print(f"   Symbol: {data['symbol']} @ {data['timeframe']}")
        print(f"   Date Range: {data['start_date']} → {data['end_date']}")
        print(f"   Total Trades: {data['total_trades']}")
        print(f"   Win Rate: {data['win_rate'] * 100:.2f}%" if data['win_rate'] else "")
        print(f"   Total PnL: ${data['total_pnl']:.2f}" if data['total_pnl'] else "")
        print(f"   Sharpe: {data['sharpe_ratio']:.3f}" if data['sharpe_ratio'] else "")
    
    elif command == "compare":
        if len(sys.argv) < 3:
            print("Error: At least one run_id required")
            sys.exit(1)
        
        run_ids = [int(x) for x in sys.argv[2:]]
        df = compare_backtest_runs(run_ids)
        
        print(f"\n📊 Comparing {len(run_ids)} Backtest Runs:\n")
        print(df.to_string(index=False))
    
    elif command == "export":
        if len(sys.argv) < 4:
            print("Error: run_id and output_path required")
            sys.exit(1)
        
        run_id = int(sys.argv[2])
        output_path = Path(sys.argv[3])
        
        if output_path.suffix == ".json":
            export_backtest_to_json(run_id, output_path)
        elif output_path.suffix == ".csv":
            export_trades_to_csv(run_id, output_path)
        else:
            print("Error: output_path must end in .json or .csv")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
