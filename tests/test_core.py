"""Test suite for Iron Condor Backtester."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import modules to test
from core.indicators import compute_indicators, compute_trend_flags
from core.metrics import calculate_summary_metrics, calculate_longest_streak
from core.backtest import compute_blackout_mask, evaluate_condor_pnl
from core.resample import get_bb_window


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": close + np.random.randn(100) * 0.5,
        "high": close + abs(np.random.randn(100) * 2),
        "low": close - abs(np.random.randn(100) * 2),
        "close": close,
        "vwap": close + np.random.randn(100) * 0.3,
    })
    
    return df


def test_compute_indicators(sample_ohlcv_data):
    """Test indicator computation."""
    df = sample_ohlcv_data.copy()
    df = df.set_index("timestamp")
    
    result = compute_indicators(df, bb_window=20)
    
    # Check all indicators are computed
    assert "bb_mid" in result.columns
    assert "bb_upper" in result.columns
    assert "bb_lower" in result.columns
    assert "rsi" in result.columns
    assert "adx" in result.columns
    assert "hv" in result.columns
    
    # Check no NaN in middle of series (after warmup)
    assert not result["rsi"].iloc[30:].isna().any()
    assert not result["adx"].iloc[30:].isna().any()
    
    # Check BB ordering
    assert (result["bb_upper"] >= result["bb_mid"]).all()
    assert (result["bb_mid"] >= result["bb_lower"]).all()


def test_compute_trend_flags(sample_ohlcv_data):
    """Test trend flag computation."""
    df = sample_ohlcv_data.copy()
    df = df.set_index("timestamp")
    df = compute_indicators(df, bb_window=20)
    
    # Test VWAP Slope method
    result = compute_trend_flags(df, method="VWAP Slope")
    assert "trend_up" in result.columns
    assert "trend_down" in result.columns
    assert result["trend_up"].dtype == bool
    assert result["trend_down"].dtype == bool
    
    # Test VWAP vs SMA20 method
    result = compute_trend_flags(df, method="VWAP vs SMA20")
    assert "trend_up" in result.columns
    
    # Test ADX + DI method
    result = compute_trend_flags(df, method="ADX + DI")
    assert "trend_up" in result.columns


def test_calculate_longest_streak():
    """Test streak calculation."""
    # All True
    mask = pd.Series([True] * 10)
    assert calculate_longest_streak(mask) == 10
    
    # Alternating
    mask = pd.Series([True, False, True, False])
    assert calculate_longest_streak(mask) == 1
    
    # Streak in middle
    mask = pd.Series([False, False, True, True, True, False])
    assert calculate_longest_streak(mask) == 3
    
    # Empty
    mask = pd.Series([], dtype=bool)
    assert calculate_longest_streak(mask) == 0


def test_evaluate_condor_pnl():
    """Test iron condor P&L calculation."""
    # Win scenario (price between short strikes)
    pnl, outcome = evaluate_condor_pnl(
        exit_price=100,
        short_put=95,
        long_put=90,
        short_call=105,
        long_call=110,
        credit=0.50
    )
    assert outcome == "win"
    assert pnl > 0
    
    # Loss scenario (price above short call)
    pnl, outcome = evaluate_condor_pnl(
        exit_price=110,
        short_put=95,
        long_put=90,
        short_call=105,
        long_call=110,
        credit=0.50
    )
    assert outcome == "loss"
    assert pnl < 0


def test_compute_blackout_mask():
    """Test blackout mask computation."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    blackout_date = pd.Timestamp("2024-01-15")
    
    mask = compute_blackout_mask(
        timestamps=dates,
        blackout_dates=[blackout_date],
        days_before=3,
        days_after=1
    )
    
    assert mask.dtype == bool
    assert mask.sum() > 0  # Some dates should be blocked
    assert mask.sum() <= 5  # At most 5 days (3 before + event + 1 after)


def test_get_bb_window():
    """Test BB window calculation."""
    assert get_bb_window("Daily") == 20
    assert get_bb_window("Hourly") == int(20 * 6.5)
    assert get_bb_window("1-minute") == int(20 * 390)


def test_calculate_summary_metrics_empty():
    """Test metrics calculation with empty dataframes."""
    trades_df = pd.DataFrame()
    equity_df = pd.DataFrame()
    
    metrics = calculate_summary_metrics(trades_df, equity_df)
    
    assert metrics["trades"] == 0
    assert metrics["total_pnl"] == 0.0
    assert metrics["win_rate"] == 0.0


def test_calculate_summary_metrics_with_trades():
    """Test metrics calculation with sample trades."""
    trades_df = pd.DataFrame({
        "pnl": [100, -50, 75, -30, 120],
        "outcome": ["win", "loss", "win", "loss", "win"],
        "short_put": [95, 94, 96, 95, 97],
        "long_put": [90, 89, 91, 90, 92],
        "short_call": [105, 106, 104, 105, 103],
        "long_call": [110, 111, 109, 110, 108],
        "net_credit": [0.5, 0.5, 0.5, 0.5, 0.5],
    })
    
    equity_df = pd.DataFrame({
        "cash": [100, 50, 125, 95, 215]
    }, index=pd.date_range("2024-01-01", periods=5, freq="D"))
    
    metrics = calculate_summary_metrics(trades_df, equity_df)
    
    assert metrics["trades"] == 5
    assert metrics["wins"] == 3
    assert metrics["losses"] == 2
    assert metrics["win_rate"] == 60.0
    assert metrics["total_pnl"] == 215.0
    assert metrics["avg_pnl"] == 43.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
