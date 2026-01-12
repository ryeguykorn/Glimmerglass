"""Timeframe resampling module."""

import pandas as pd
import streamlit as st
from typing import Dict

from config import TIMEFRAME_TO_FREQ, TIMEFRAME_BB_MULTIPLIERS, BB_BASE_WINDOW


def get_freq_string(timeframe: str) -> str:
    """
    Get pandas frequency string for timeframe.
    
    Args:
        timeframe: Human-readable timeframe (e.g., "5-minute")
        
    Returns:
        Pandas frequency string (e.g., "5min")
    """
    return TIMEFRAME_TO_FREQ.get(timeframe, "D")


def get_bb_window(timeframe: str, base_days: int = BB_BASE_WINDOW) -> int:
    """
    Calculate Bollinger Band window size for given timeframe.
    
    Maintains approximately constant time period (~20 trading days).
    
    Args:
        timeframe: Selected timeframe
        base_days: Base window in days (default 20)
        
    Returns:
        Number of bars for BB calculation
    """
    multiplier = TIMEFRAME_BB_MULTIPLIERS.get(timeframe, 1.0)
    return int(base_days * multiplier)


@st.cache_data(show_spinner=False)
def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample OHLCV data to specified timeframe.
    
    Aggregation rules:
    - Open: first
    - High: max
    - Low: min
    - Close: last
    - VWAP: mean
    - Volume: sum (if present)
    
    Args:
        df: DataFrame with timestamp index
        timeframe: Target timeframe
        
    Returns:
        Resampled DataFrame with complete bars only
        
    Raises:
        ValueError: If timestamp column missing or invalid
    """
    if df.empty:
        return df
    
    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must have 'timestamp' column")
    
    freq = get_freq_string(timeframe)
    
    # Prepare for resampling
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    
    # Define aggregation rules
    agg_dict: Dict[str, str] = {}
    
    if "open" in df.columns:
        agg_dict["open"] = "first"
    if "high" in df.columns:
        agg_dict["high"] = "max"
    if "low" in df.columns:
        agg_dict["low"] = "min"
    if "close" in df.columns:
        agg_dict["close"] = "last"
    if "vwap" in df.columns:
        agg_dict["vwap"] = "mean"
    if "volume" in df.columns:
        agg_dict["volume"] = "sum"
    
    # Resample
    df_resampled = df.resample(freq).agg(agg_dict)
    
    # Drop incomplete bars (any NaN values)
    df_resampled = df_resampled.dropna(how="any")
    
    return df_resampled.reset_index()
