"""High-performance backtest engine using numpy arrays."""

import pandas as pd
import numpy as np
import gc
from typing import List, Optional, Tuple
from datetime import timedelta

from config import (
    PER_LEG_FEE,
    CONTRACT_MULTIPLIER,
    DEFAULT_WING_WIDTH,
    DEFAULT_CREDIT_MULTIPLIER,
    ADX_ENTRY_THRESHOLD,
    RSI_LOWER_BOUND,
    RSI_UPPER_BOUND,
    PROGRESS_UPDATE_INTERVAL,
)
from core.types import Position, BacktestResult
from core.indicators import compute_indicators, compute_trend_flags


def compute_blackout_mask(
    timestamps: pd.DatetimeIndex,
    blackout_dates: List[pd.Timestamp],
    days_before: int,
    days_after: int
) -> np.ndarray:
    """
    Vectorized blackout window mask computation.
    
    Args:
        timestamps: DatetimeIndex of bar timestamps
        blackout_dates: List of earnings/event dates
        days_before: Days before event to block
        days_after: Days after event to block
        
    Returns:
        Boolean array (True = blackout period)
    """
    if not blackout_dates or len(timestamps) == 0:
        return np.zeros(len(timestamps), dtype=bool)
    
    # Normalize all timestamps to dates
    dates_norm = pd.to_datetime(timestamps).normalize()
    mask = np.zeros(len(dates_norm), dtype=bool)
    
    for event_date in blackout_dates:
        event_norm = pd.Timestamp(event_date).normalize()
        window_start = event_norm - timedelta(days=days_before)
        window_end = event_norm + timedelta(days=days_after)
        
        # Union of blackout windows
        in_window = (dates_norm >= window_start) & (dates_norm <= window_end)
        mask |= in_window
    
    return mask


def evaluate_condor_pnl(
    exit_price: float,
    short_put: float,
    long_put: float,
    short_call: float,
    long_call: float,
    credit: float
) -> Tuple[float, str]:
    """
    Evaluate iron condor P&L at exit.
    
    Args:
        exit_price: Price at exit
        short_put: Short put strike
        long_put: Long put strike
        short_call: Short call strike
        long_call: Long call strike
        credit: Net credit received at entry
        
    Returns:
        (pnl, outcome) tuple
    """
    put_width = short_put - long_put
    call_width = long_call - short_call
    
    # Win if price stays between short strikes
    if short_put <= exit_price <= short_call:
        pnl = credit * CONTRACT_MULTIPLIER - 4 * PER_LEG_FEE
        return pnl, "win"
    
    # Loss - price breached a short strike
    loss_width = call_width if exit_price > short_call else put_width
    pnl = -(loss_width - credit) * CONTRACT_MULTIPLIER - 4 * PER_LEG_FEE
    return pnl, "loss"


def run_backtest(
    df: pd.DataFrame,
    blackout_dates: List[pd.Timestamp],
    hv_min: float,
    hv_max: float,
    adx_exit_threshold: int,
    vwap_exit_k: float,
    use_bias: bool,
    bias_strength: float,
    trend_method: str,
    wing_ext_pct: float,
    days_before: int,
    days_after: int,
    bb_window: int,
    progress_callback: Optional[any] = None,
) -> BacktestResult:
    """
    Execute iron condor backtest with rule-based exits.
    
    Strategy Logic:
    1. Entry Filters:
       - ADX < 20 (low trend strength)
       - RSI between 40-60 (neutral momentum)
       - HV within specified range
       - Outside blackout windows
    
    2. Strike Selection:
       - Short strikes at Bollinger Band edges (on VWAP)
       - Long strikes 5 points wider (or extended based on regime)
       - Optional bias adjustment for trending markets
    
    3. Exit Rules (checked in order):
       - Broke: Price exceeds long strikes → immediate exit
       - Breach: Price exceeds short strikes → immediate exit
       - ADX Exit: ADX rises above threshold → trend emerging
       - VWAP Exit: VWAP slope reversal + price divergence
       - Expiry: Held to expiration (next Friday or 5 bars max)
    
    Args:
        df: DataFrame with OHLCV + VWAP (will be reindexed by timestamp)
        blackout_dates: Earnings/event dates to avoid
        hv_min: Minimum historical volatility for entry
        hv_max: Maximum historical volatility for entry
        adx_exit_threshold: ADX level triggering exit
        vwap_exit_k: VWAP distance multiplier for exit
        use_bias: Enable trend-based strike adjustment
        bias_strength: Dollar amount of bias shift
        trend_method: Method for trend detection
        wing_ext_pct: Percentage extension for wing width in special regimes
        days_before: Days before earnings to block entries
        days_after: Days after earnings to block entries
        bb_window: Bollinger Band lookback period
        progress_callback: Optional Streamlit progress bar
        
    Returns:
        BacktestResult with trades, equity curve, rejections, and summary
    """
    # Compute indicators once
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    
    df = compute_indicators(df, bb_window=bb_window)
    df = compute_trend_flags(df, method=trend_method)
    
    # Extract numpy arrays for fast iteration
    timestamps = df.index.to_numpy()
    n = len(timestamps)
    
    # Price arrays
    close_arr = df["close"].to_numpy(dtype=np.float64)
    vwap_arr = df["vwap"].to_numpy(dtype=np.float64)
    
    # Indicator arrays
    bb_mid = df["bb_mid"].to_numpy(dtype=np.float64)
    bb_upper = df["bb_upper"].to_numpy(dtype=np.float64)
    bb_lower = df["bb_lower"].to_numpy(dtype=np.float64)
    bb_half = (bb_upper - bb_mid).astype(np.float64)
    
    adx_arr = df["adx"].to_numpy(dtype=np.float64)
    rsi_arr = df["rsi"].to_numpy(dtype=np.float64)
    hv_arr = df["hv"].to_numpy(dtype=np.float64)
    
    # Trend flags
    trend_up = df["trend_up"].to_numpy(dtype=bool)
    trend_down = df["trend_down"].to_numpy(dtype=bool)
    bb_tightening = df["bb_tightening"].to_numpy(dtype=bool)
    
    # Entry eligibility (vectorized pre-computation)
    cond_adx = adx_arr < ADX_ENTRY_THRESHOLD
    cond_rsi = (rsi_arr >= RSI_LOWER_BOUND) & (rsi_arr <= RSI_UPPER_BOUND)
    cond_hv = (hv_arr >= hv_min) & (hv_arr <= hv_max)
    
    blackout_mask = compute_blackout_mask(df.index, blackout_dates, days_before, days_after)
    eligible = cond_adx & cond_rsi & cond_hv & (~blackout_mask)
    
    # Track rejected entries for diagnostics
    rejected_entries = []
    not_eligible_idx = np.where(~eligible)[0]
    
    for idx in not_eligible_idx:
        reasons = []
        if not cond_hv[idx]:
            reasons.append("HV outside range")
        if not cond_adx[idx]:
            reasons.append("ADX too high")
        if not cond_rsi[idx]:
            reasons.append("RSI out of range")
        if blackout_mask[idx]:
            reasons.append("Blackout window")
        
        rejected_entries.append({
            "date": timestamps[idx],
            "reasons": ", ".join(reasons) if reasons else "Not eligible",
            "adx": float(adx_arr[idx]),
            "rsi": float(rsi_arr[idx]),
            "hv": float(hv_arr[idx]),
            "blackout": bool(blackout_mask[idx]),
        })
    
    # State tracking
    open_positions: List[Position] = []
    trades = []
    cash = 0.0
    equity_curve = []
    
    # Progress tracking
    if progress_callback is not None:
        progress_callback.progress(0)
    
    update_freq = max(1, int(n * PROGRESS_UPDATE_INTERVAL))
    
    # Helper for strike rounding
    def round_strike(value: float, step: float = 1.0) -> float:
        return float(np.round(value / step) * step)
    
    # Main backtest loop
    for i in range(n):
        current_price = close_arr[i]
        
        # ==================== EXIT PROCESSING ====================
        if open_positions:
            remaining_positions = []
            current_adx = adx_arr[i]
            adx_triggered = current_adx >= adx_exit_threshold
            
            # VWAP exit logic
            if i > 1:
                vwap_delta_today = vwap_arr[i] - vwap_arr[i-1]
                vwap_delta_prev = vwap_arr[i-1] - vwap_arr[i-2]
                
                sign_today = np.sign(vwap_delta_today)
                sign_prev = np.sign(vwap_delta_prev)
                
                slope_reversal = (sign_today != 0 and sign_prev != 0 and sign_today != sign_prev)
                
                acceptance_distance = vwap_exit_k * bb_half[i]
                price_diverged = abs(current_price - vwap_arr[i]) >= acceptance_distance
                price_on_slope_side = (
                    (vwap_delta_today > 0 and current_price > vwap_arr[i]) or
                    (vwap_delta_today < 0 and current_price < vwap_arr[i])
                )
                
                vwap_exit_triggered = slope_reversal and price_diverged and price_on_slope_side
            else:
                vwap_exit_triggered = False
            
            for pos in open_positions:
                should_exit = False
                exit_reason = None
                
                # Check exit conditions (only before expiry)
                if i < pos.expiry_idx:
                    # 1. Broke long strikes
                    if current_price < pos.long_put or current_price > pos.long_call:
                        should_exit = True
                        exit_reason = "broke"
                    
                    # 2. Breached short strikes
                    elif current_price < pos.short_put or current_price > pos.short_call:
                        should_exit = True
                        exit_reason = "breach"
                    
                    # 3. ADX exit
                    elif adx_triggered:
                        should_exit = True
                        exit_reason = "adx_exit"
                    
                    # 4. VWAP exit
                    elif vwap_exit_triggered:
                        should_exit = True
                        exit_reason = "vwap_exit"
                
                if should_exit:
                    pnl, _ = evaluate_condor_pnl(
                        current_price,
                        pos.short_put, pos.long_put,
                        pos.short_call, pos.long_call,
                        pos.credit
                    )
                    cash += pnl
                    
                    trades.append({
                        "entry_date": timestamps[pos.entry_idx],
                        "expiry_date": timestamps[i],
                        "short_put": pos.short_put,
                        "long_put": pos.long_put,
                        "short_call": pos.short_call,
                        "long_call": pos.long_call,
                        "net_credit": pos.credit,
                        "expiry_close": current_price,
                        "pnl": pnl,
                        "outcome": exit_reason
                    })
                else:
                    remaining_positions.append(pos)
            
            open_positions = remaining_positions
        
        # ==================== EXPIRATION HANDLING ====================
        if open_positions:
            remaining_positions = []
            for pos in open_positions:
                if i == pos.expiry_idx:
                    # Position expired
                    pnl, outcome = evaluate_condor_pnl(
                        current_price,
                        pos.short_put, pos.long_put,
                        pos.short_call, pos.long_call,
                        pos.credit
                    )
                    cash += pnl
                    
                    trades.append({
                        "entry_date": timestamps[pos.entry_idx],
                        "expiry_date": timestamps[i],
                        "short_put": pos.short_put,
                        "long_put": pos.long_put,
                        "short_call": pos.short_call,
                        "long_call": pos.long_call,
                        "net_credit": pos.credit,
                        "expiry_close": current_price,
                        "pnl": pnl,
                        "outcome": outcome
                    })
                else:
                    remaining_positions.append(pos)
            
            open_positions = remaining_positions
        
        # ==================== ENTRY EVALUATION ====================
        if eligible[i]:
            # Determine strikes based on bias
            if use_bias:
                bias = float(bias_strength)
                if trend_up[i]:
                    short_put = round_strike(bb_lower[i] + 0.5 * bias)
                    short_call = round_strike(bb_upper[i] + 1.0 * bias)
                elif trend_down[i]:
                    short_put = round_strike(bb_lower[i] - 1.0 * bias)
                    short_call = round_strike(bb_upper[i] - 0.5 * bias)
                else:
                    short_put = round_strike(bb_lower[i])
                    short_call = round_strike(bb_upper[i])
            else:
                short_put = round_strike(bb_lower[i])
                short_call = round_strike(bb_upper[i])
            
            # Determine wing widths (may extend in special regimes)
            prev_trend_up = bool(trend_up[i-1]) if i > 0 else False
            prev_trend_down = bool(trend_down[i-1]) if i > 0 else False
            is_tightening = bool(bb_tightening[i])
            
            extension = 1.0 + max(0.0, wing_ext_pct) / 100.0
            
            put_wing = DEFAULT_WING_WIDTH * extension \
                if (trend_up[i] and prev_trend_down and is_tightening) \
                else DEFAULT_WING_WIDTH
            
            call_wing = DEFAULT_WING_WIDTH * extension \
                if (trend_down[i] and prev_trend_up and is_tightening) \
                else DEFAULT_WING_WIDTH
            
            long_put = round_strike(short_put - put_wing)
            long_call = round_strike(short_call + call_wing)
            
            # Credit estimation
            min_wing = min(call_wing, put_wing)
            credit = DEFAULT_CREDIT_MULTIPLIER * min_wing
            
            # Find expiry (next Friday within 5 bars, else max window)
            expiry_idx = None
            search_end = min(i + 5, n - 1)
            
            for j in range(i, search_end + 1):
                if pd.Timestamp(timestamps[j]).weekday() == 4:  # Friday
                    expiry_idx = j
                    break
            
            if expiry_idx is None:
                expiry_idx = search_end
            
            # Create position
            position = Position(
                entry_idx=i,
                expiry_idx=expiry_idx,
                short_put=short_put,
                long_put=long_put,
                short_call=short_call,
                long_call=long_call,
                credit=credit
            )
            open_positions.append(position)
        
        # Update equity curve
        equity_curve.append({"date": timestamps[i], "cash": cash})
        
        # Update progress
        if progress_callback is not None and (i % update_freq == 0 or i == n - 1):
            progress_pct = int((i + 1) * 100 / n)
            progress_callback.progress(progress_pct)
    
    # Build result DataFrames
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df["cum_pnl"] = trades_df["pnl"].cumsum()
    
    equity_df = pd.DataFrame(equity_curve)
    if not equity_df.empty:
        equity_df = equity_df.set_index("date")
    
    rejected_df = pd.DataFrame(rejected_entries)
    
    # Compute summary metrics (delegate to metrics module)
    from core.metrics import calculate_summary_metrics
    summary = calculate_summary_metrics(trades_df, equity_df)
    
    # Memory cleanup
    del (close_arr, vwap_arr, bb_mid, bb_upper, bb_lower, bb_half,
         adx_arr, rsi_arr, hv_arr, trend_up, trend_down, bb_tightening,
         eligible, blackout_mask)
    gc.collect()
    
    return BacktestResult(
        df_indicators=df,
        trades=trades_df,
        equity_curve=equity_df,
        rejected=rejected_df,
        summary=summary
    )
