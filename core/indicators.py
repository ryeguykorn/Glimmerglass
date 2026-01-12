"""Technical indicators computation module."""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Literal

from config import (
    RSI_PERIOD,
    ADX_PERIOD,
    BB_STD_MULTIPLIER,
    HV_WINDOW,
    VWAP_SMA_WINDOW,
    BB_TIGHTENING_WINDOW,
    ANNUALIZATION_FACTOR,
    MAX_CACHE_ENTRIES,
)


@st.cache_data(show_spinner=False, max_entries=MAX_CACHE_ENTRIES)
def compute_indicators(df: pd.DataFrame, bb_window: int) -> pd.DataFrame:
    """
    Compute all technical indicators for backtest.
    
    Indicators calculated:
    - Bollinger Bands (on VWAP)
    - RSI
    - ADX & Directional Indicators (DI+, DI-)
    - ATR
    - Historical Volatility
    - VWAP SMA
    - BB Width & Tightening
    
    Args:
        df: DataFrame with OHLCV + VWAP columns
        bb_window: Bollinger Band lookback period
        
    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()
    
    # Bollinger Bands on VWAP
    ma_vwap = df["vwap"].rolling(bb_window, min_periods=bb_window).mean()
    std_vwap = df["vwap"].rolling(bb_window, min_periods=bb_window).std(ddof=0)
    
    df["bb_mid"] = ma_vwap
    df["bb_upper"] = ma_vwap + BB_STD_MULTIPLIER * std_vwap
    df["bb_lower"] = ma_vwap - BB_STD_MULTIPLIER * std_vwap
    
    # RSI (14-period)
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/RSI_PERIOD, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = (100 - (100 / (1 + rs))).bfill().ffill()
    
    # ADX & Directional Indicators
    up_move = df["high"].diff()
    down_move = df["low"].diff() * -1
    
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move
    
    # True Range
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs()
    ], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/ADX_PERIOD, adjust=False).mean()
    df["atr"] = atr
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/ADX_PERIOD, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/ADX_PERIOD, adjust=False).mean() / atr)
    
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df["adx"] = dx.ewm(alpha=1/ADX_PERIOD, adjust=False).mean().bfill().ffill()
    
    # VWAP SMA
    df["vwap_sma20"] = df["vwap"].rolling(VWAP_SMA_WINDOW).mean()
    
    # BB Width and Tightening
    df["bb_width"] = df["bb_upper"] - df["bb_lower"]
    df["bb_tightening"] = (
        (df["bb_width"] < df["bb_width"].shift(1)) &
        (df["bb_width"] < df["bb_width"].rolling(BB_TIGHTENING_WINDOW, min_periods=5).median())
    ).fillna(False)
    
    # Historical Volatility (21-day, annualized)
    log_returns = np.log(df["close"]).diff()
    df["hv"] = (
        log_returns.rolling(HV_WINDOW).std(ddof=0) * 
        np.sqrt(ANNUALIZATION_FACTOR) * 100
    ).bfill().ffill()
    
    return df


TrendMethod = Literal["VWAP Slope", "VWAP vs SMA20", "ADX + DI"]


def compute_trend_flags(
    df: pd.DataFrame,
    method: TrendMethod = "VWAP Slope"
) -> pd.DataFrame:
    """
    Compute trend direction flags based on selected method.
    
    Methods:
    - VWAP Slope: Trend based on VWAP delta (up if rising, down if falling)
    - VWAP vs SMA20: Trend based on VWAP relative to its 20-period SMA
    - ADX + DI: Trend based on directional indicators with ADX strength filter
    
    Args:
        df: DataFrame with computed indicators
        method: Trend detection method
        
    Returns:
        DataFrame with trend_up and trend_down boolean columns
    """
    df = df.copy()
    
    if method == "VWAP Slope":
        df["vwap_delta"] = df["vwap"].diff()
        df["trend_up"] = df["vwap_delta"] > 0
        df["trend_down"] = df["vwap_delta"] < 0
        
    elif method == "VWAP vs SMA20":
        df["trend_up"] = df["vwap"] > df["vwap_sma20"]
        df["trend_down"] = df["vwap"] < df["vwap_sma20"]
        
    elif method == "ADX + DI":
        df["trend_up"] = (df["plus_di"] > df["minus_di"]) & (df["adx"] > 20)
        df["trend_down"] = (df["minus_di"] > df["plus_di"]) & (df["adx"] > 20)
        
    else:
        # No trend detection
        df["trend_up"] = False
        df["trend_down"] = False
    
    return df


def validate_indicators(df: pd.DataFrame) -> bool:
    """
    Check if all required indicators are present and valid.
    
    Args:
        df: DataFrame with indicators
        
    Returns:
        True if all indicators present and contain valid data
    """
    required_indicators = [
        "bb_mid", "bb_upper", "bb_lower",
        "rsi", "adx", "plus_di", "minus_di",
        "hv", "vwap_sma20", "bb_width", "bb_tightening"
    ]
    
    for indicator in required_indicators:
        if indicator not in df.columns:
            return False
        if df[indicator].isna().all():
            return False
    
    return True
