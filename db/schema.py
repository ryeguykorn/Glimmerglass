"""
SQLite schema for Tier 0 local metadata storage.
"""
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime


DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "tier0.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get SQLite connection with optimized settings."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    
    # Performance optimizations
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY")
    
    return conn


def init_database(conn: sqlite3.Connection) -> None:
    """Initialize all tables for Tier 0."""
    
    # Symbols table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            asset_type TEXT NOT NULL,
            vendor TEXT NOT NULL DEFAULT 'csv_import',
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(asset_type)")
    
    # Datasets table - tracks parquet files
    conn.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol_id INTEGER NOT NULL,
            timeframe TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            file_size_bytes INTEGER NOT NULL,
            checksum TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (symbol_id) REFERENCES symbols(symbol_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_datasets_symbol ON datasets(symbol_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_datasets_timeframe ON datasets(timeframe)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_datasets_dates ON datasets(start_date, end_date)")
    
    # Backtest runs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
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
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_dataset ON backtest_runs(dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_dates ON backtest_runs(start_date, end_date)")
    
    # Trade log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
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
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(entry_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl)")
    
    # Metadata key-value store
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    conn.commit()


def add_symbol(conn: sqlite3.Connection, symbol: str, asset_type: str = "equity", 
               vendor: str = "csv_import", description: str = None) -> int:
    """Add or update symbol, return symbol_id."""
    cursor = conn.execute(
        """
        INSERT INTO symbols (symbol, asset_type, vendor, description, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(symbol) DO UPDATE SET
            asset_type = excluded.asset_type,
            vendor = excluded.vendor,
            description = excluded.description,
            updated_at = datetime('now')
        RETURNING symbol_id
        """,
        (symbol, asset_type, vendor, description)
    )
    result = cursor.fetchone()[0]
    conn.commit()
    return result


def add_dataset(conn: sqlite3.Connection, symbol_id: int, timeframe: str,
                start_date: str, end_date: str, row_count: int, 
                file_path: str, file_size: int, checksum: str = None) -> int:
    """Register a parquet dataset."""
    cursor = conn.execute(
        """
        INSERT INTO datasets (symbol_id, timeframe, start_date, end_date, 
                            row_count, file_path, file_size_bytes, checksum)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING dataset_id
        """,
        (symbol_id, timeframe, start_date, end_date, row_count, file_path, file_size, checksum)
    )
    result = cursor.fetchone()[0]
    conn.commit()
    return result


def get_datasets(conn: sqlite3.Connection, symbol: str = None, 
                 timeframe: str = None) -> list:
    """Query available datasets."""
    query = """
        SELECT d.*, s.symbol, s.asset_type
        FROM datasets d
        JOIN symbols s ON d.symbol_id = s.symbol_id
        WHERE 1=1
    """
    params = []
    
    if symbol:
        query += " AND s.symbol = ?"
        params.append(symbol)
    if timeframe:
        query += " AND d.timeframe = ?"
        params.append(timeframe)
    
    query += " ORDER BY s.symbol, d.timeframe, d.start_date"
    
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def add_backtest_run(conn: sqlite3.Connection, dataset_id: int, config: dict,
                     start_date: str, end_date: str, metrics: dict, 
                     runtime: float, run_name: str = None) -> int:
    """Save backtest run metadata."""
    import json
    
    cursor = conn.execute(
        """
        INSERT INTO backtest_runs (
            dataset_id, run_name, config_json, start_date, end_date,
            total_trades, win_rate, avg_pnl, total_pnl, 
            sharpe_ratio, max_drawdown, runtime_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING run_id
        """,
        (
            dataset_id, run_name, json.dumps(config), start_date, end_date,
            metrics.get("total_trades", 0),
            metrics.get("win_rate"),
            metrics.get("avg_pnl"),
            metrics.get("total_pnl"),
            metrics.get("sharpe_ratio"),
            metrics.get("max_drawdown"),
            runtime
        )
    )
    result = cursor.fetchone()[0]
    conn.commit()
    return result


def add_trades(conn: sqlite3.Connection, run_id: int, trades: list) -> None:
    """Bulk insert trades from backtest."""
    conn.executemany(
        """
        INSERT INTO trades (
            run_id, entry_date, exit_date, days_held, pnl, pnl_pct,
            status, entry_reason, exit_reason, strike_width, 
            distance_from_price, iv_rank
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                t.get("entry_date"),
                t.get("exit_date"),
                t.get("days_held"),
                t.get("pnl"),
                t.get("pnl_pct"),
                t.get("status"),
                t.get("entry_reason"),
                t.get("exit_reason"),
                t.get("strike_width"),
                t.get("distance_from_price"),
                t.get("iv_rank")
            )
            for t in trades
        ]
    )
    conn.commit()


def get_backtest_runs(conn: sqlite3.Connection, dataset_id: int = None, 
                      limit: int = 50) -> list:
    """Query backtest run history."""
    query = """
        SELECT br.*, d.file_path, s.symbol, d.timeframe
        FROM backtest_runs br
        JOIN datasets d ON br.dataset_id = d.dataset_id
        JOIN symbols s ON d.symbol_id = s.symbol_id
        WHERE 1=1
    """
    params = []
    
    if dataset_id:
        query += " AND br.dataset_id = ?"
        params.append(dataset_id)
    
    query += " ORDER BY br.created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    # Test database creation
    conn = get_connection()
    init_database(conn)
    
    print("✅ Database initialized at", DEFAULT_DB_PATH)
    
    # Show tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📊 Tables created: {', '.join(tables)}")
    
    conn.close()
