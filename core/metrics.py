"""Performance metrics calculation module."""

import pandas as pd
import numpy as np
from typing import Dict

from config import PER_LEG_FEE, CONTRACT_MULTIPLIER


def calculate_summary_metrics(
    trades_df: pd.DataFrame,
    equity_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate comprehensive backtest performance metrics.
    
    Metrics computed:
    - Trade counts (total, wins, losses, by exit type)
    - Win rate
    - Total P&L
    - Best/worst trades
    - Average P&L and risk
    - Max drawdown ($ and %)
    - Profit factor
    - Reward/risk ratio
    - Win/loss streaks
    - Return on risk
    
    Args:
        trades_df: DataFrame of executed trades
        equity_df: DataFrame of equity curve
        
    Returns:
        Dictionary of metric name -> value
    """
    metrics = {}
    
    if trades_df.empty:
        # Return empty metrics
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "breaches": 0,
            "adx_exits": 0,
            "vwap_exits": 0,
            "brokes": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "reward_risk_ratio": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "win_streak": 0,
            "loss_streak": 0,
            "return_on_risk_pct": 0.0,
        }
    
    # Basic counts
    metrics["trades"] = int(len(trades_df))
    
    # Outcome breakdown
    wins_mask = trades_df["outcome"] == "win"
    losses_mask = trades_df["outcome"] == "loss"
    
    metrics["wins"] = int(wins_mask.sum())
    metrics["losses"] = int(losses_mask.sum())
    metrics["breaches"] = int((trades_df["outcome"] == "breach").sum())
    metrics["adx_exits"] = int((trades_df["outcome"] == "adx_exit").sum())
    metrics["vwap_exits"] = int((trades_df["outcome"] == "vwap_exit").sum())
    metrics["brokes"] = int((trades_df["outcome"] == "broke").sum())
    
    # Win rate
    metrics["win_rate"] = float(100.0 * metrics["wins"] / metrics["trades"]) \
        if metrics["trades"] > 0 else 0.0
    
    # P&L metrics
    pnl_series = trades_df["pnl"]
    metrics["total_pnl"] = float(pnl_series.sum())
    metrics["avg_pnl"] = float(pnl_series.mean())
    metrics["best_trade"] = float(pnl_series.max())
    metrics["worst_trade"] = float(pnl_series.min())
    
    # Win/loss statistics
    if metrics["wins"] > 0:
        win_pnl = pnl_series[wins_mask]
        metrics["avg_win"] = float(win_pnl.mean())
        metrics["total_wins"] = float(win_pnl.sum())
    else:
        metrics["avg_win"] = 0.0
        metrics["total_wins"] = 0.0
    
    if metrics["losses"] > 0:
        loss_pnl = pnl_series[losses_mask]
        metrics["avg_loss"] = float(abs(loss_pnl.mean()))
        metrics["total_losses"] = float(abs(loss_pnl.sum()))
    else:
        metrics["avg_loss"] = 0.0
        metrics["total_losses"] = 0.0
    
    # Profit factor
    if metrics["total_losses"] > 0:
        metrics["profit_factor"] = float(metrics["total_wins"] / metrics["total_losses"])
    else:
        metrics["profit_factor"] = float('inf') if metrics["total_wins"] > 0 else 0.0
    
    # Reward/risk ratio
    if metrics["avg_loss"] > 0 and metrics["avg_win"] > 0:
        metrics["reward_risk_ratio"] = float(metrics["avg_win"] / metrics["avg_loss"])
    else:
        metrics["reward_risk_ratio"] = 0.0
    
    # Streaks
    metrics["win_streak"] = calculate_longest_streak(wins_mask)
    metrics["loss_streak"] = calculate_longest_streak(losses_mask)
    
    # Risk metrics
    if "short_put" in trades_df.columns and "long_put" in trades_df.columns:
        put_width = trades_df["short_put"] - trades_df["long_put"]
        call_width = trades_df["long_call"] - trades_df["short_call"]
        wing_width = np.minimum(put_width, call_width)
        
        max_risk_per_trade = (
            (wing_width - trades_df["net_credit"]) * CONTRACT_MULTIPLIER +
            4 * PER_LEG_FEE
        )
        
        metrics["avg_risk"] = float(max_risk_per_trade.mean())
        metrics["total_risk"] = float(max_risk_per_trade.sum())
        
        if metrics["total_risk"] > 0:
            metrics["return_on_risk_pct"] = float(
                100.0 * metrics["total_pnl"] / metrics["total_risk"]
            )
        else:
            metrics["return_on_risk_pct"] = 0.0
    else:
        metrics["avg_risk"] = 0.0
        metrics["total_risk"] = 0.0
        metrics["return_on_risk_pct"] = 0.0
    
    # Drawdown metrics
    if not equity_df.empty and "cash" in equity_df.columns:
        equity_series = equity_df["cash"]
        running_max = equity_series.cummax()
        drawdown = running_max - equity_series
        
        metrics["max_drawdown"] = float(drawdown.max())
        
        if metrics["max_drawdown"] > 0:
            dd_idx = drawdown.idxmax()
            peak_value = running_max.loc[dd_idx]
            if peak_value != 0:
                metrics["max_drawdown_pct"] = float(
                    100.0 * metrics["max_drawdown"] / peak_value
                )
            else:
                metrics["max_drawdown_pct"] = 0.0
        else:
            metrics["max_drawdown_pct"] = 0.0
    else:
        metrics["max_drawdown"] = 0.0
        metrics["max_drawdown_pct"] = 0.0
    
    return metrics


def calculate_longest_streak(mask: pd.Series) -> int:
    """
    Calculate longest consecutive True streak in boolean series.
    
    Args:
        mask: Boolean Series
        
    Returns:
        Length of longest streak
    """
    longest = 0
    current = 0
    
    for value in mask.tolist():
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    
    return longest


def calculate_monthly_breakdown(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate trades by month.
    
    Args:
        trades_df: Trades DataFrame with expiry_date column
        
    Returns:
        DataFrame with columns: month, trades, pnl, win_rate
    """
    if trades_df.empty or "expiry_date" not in trades_df.columns:
        return pd.DataFrame(columns=["month", "trades", "pnl", "win_rate"])
    
    df = trades_df.copy()
    df["month"] = pd.to_datetime(df["expiry_date"]).dt.to_period("M").astype(str)
    
    monthly = df.groupby("month").agg({
        "pnl": ["sum", "count"],
        "outcome": lambda x: 100.0 * (x == "win").sum() / len(x)
    }).reset_index()
    
    monthly.columns = ["month", "pnl", "trades", "win_rate"]
    monthly = monthly.sort_values("month")
    
    return monthly


def calculate_trade_distribution(trades_df: pd.DataFrame, bins: int = 20) -> Dict:
    """
    Calculate P&L distribution statistics.
    
    Args:
        trades_df: Trades DataFrame
        bins: Number of histogram bins
        
    Returns:
        Dictionary with histogram data and statistics
    """
    if trades_df.empty or "pnl" not in trades_df.columns:
        return {
            "bins": [],
            "counts": [],
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "skew": 0.0,
        }
    
    pnl = trades_df["pnl"]
    
    counts, bin_edges = np.histogram(pnl, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    return {
        "bins": bin_centers.tolist(),
        "counts": counts.tolist(),
        "mean": float(pnl.mean()),
        "median": float(pnl.median()),
        "std": float(pnl.std()),
        "skew": float(pnl.skew()) if len(pnl) > 2 else 0.0,
    }
