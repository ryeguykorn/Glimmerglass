"""Export utilities for CSV and JSON data."""

import pandas as pd
import json
import uuid
from datetime import datetime
from typing import Dict, Any

from config import EXPORT_DATETIME_FORMAT, VERSION


def export_trades_csv(trades_df: pd.DataFrame) -> str:
    """
    Export trades DataFrame to CSV string.
    
    Args:
        trades_df: Trades DataFrame
        
    Returns:
        CSV string
    """
    if trades_df.empty:
        return "No trades to export"
    
    df = trades_df.copy()
    
    # Format dates
    for col in ["entry_date", "expiry_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime(EXPORT_DATETIME_FORMAT)
    
    return df.to_csv(index=False)


def export_equity_csv(equity_df: pd.DataFrame) -> str:
    """
    Export equity curve to CSV string.
    
    Args:
        equity_df: Equity DataFrame with date index
        
    Returns:
        CSV string
    """
    if equity_df.empty:
        return "No equity data to export"
    
    df = equity_df.copy()
    df.index = pd.to_datetime(df.index).strftime(EXPORT_DATETIME_FORMAT)
    df.index.name = "timestamp"
    
    return df.to_csv()


def export_rejected_csv(rejected_df: pd.DataFrame) -> str:
    """
    Export rejected evaluations to CSV string.
    
    Args:
        rejected_df: Rejected evaluations DataFrame
        
    Returns:
        CSV string
    """
    if rejected_df.empty:
        return "No rejections to export"
    
    df = rejected_df.copy()
    
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime(EXPORT_DATETIME_FORMAT)
    
    return df.to_csv(index=False)


def export_run_config_json(
    data_info: Dict[str, Any],
    parameters: Dict[str, Any],
    summary: Dict[str, Any]
) -> str:
    """
    Export run configuration and results to JSON string.
    
    Args:
        data_info: Information about input data
        parameters: Backtest parameters
        summary: Summary metrics
        
    Returns:
        Formatted JSON string
    """
    config = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "data": data_info,
        "parameters": parameters,
        "results": summary
    }
    
    return json.dumps(config, indent=2, default=str)
