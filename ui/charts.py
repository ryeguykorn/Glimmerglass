"""Chart generation module using Plotly."""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List

from config import (
    CHART_TEMPLATE,
    THEME_COLORS,
    EQUITY_LINE_WIDTH,
    INDICATOR_LINE_WIDTH,
    MARKER_SIZE,
)


def create_equity_chart(equity_df: pd.DataFrame) -> go.Figure:
    """Create equity curve chart."""
    fig = go.Figure()
    
    if not equity_df.empty and "cash" in equity_df.columns:
        fig.add_trace(go.Scatter(
            x=equity_df.index,
            y=equity_df["cash"],
            name="Equity",
            mode="lines",
            line=dict(color=THEME_COLORS["secondary"], width=EQUITY_LINE_WIDTH),
            fill='tozeroy',
            fillcolor=f"{THEME_COLORS['secondary']}20"
        ))
    
    fig.update_layout(
        template=CHART_TEMPLATE,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Cash ($)",
        hovermode='x unified',
        showlegend=False
    )
    
    return fig


def create_drawdown_chart(equity_df: pd.DataFrame) -> go.Figure:
    """Create drawdown overlay chart."""
    fig = go.Figure()
    
    if not equity_df.empty and "cash" in equity_df.columns:
        running_max = equity_df["cash"].cummax()
        drawdown = running_max - equity_df["cash"]
        
        fig.add_trace(go.Scatter(
            x=equity_df.index,
            y=-drawdown,
            name="Drawdown",
            mode="lines",
            line=dict(color=THEME_COLORS["error"], width=2),
            fill='tozeroy',
            fillcolor=f"{THEME_COLORS['error']}30"
        ))
    
    fig.update_layout(
        template=CHART_TEMPLATE,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Drawdown ($)",
        hovermode='x unified',
        showlegend=False
    )
    
    return fig


def create_price_chart(
    df: pd.DataFrame,
    trades_df: pd.DataFrame,
    blackout_dates: List[pd.Timestamp],
    days_before: int,
    days_after: int,
    show_trend: bool = False
) -> go.Figure:
    """Create comprehensive price chart with indicators and trade markers."""
    fig = go.Figure()
    
    # VWAP and Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=df["vwap"],
        name="VWAP",
        mode="lines",
        line=dict(color="steelblue", width=2.5)
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df["bb_upper"],
        name="BB Upper",
        mode="lines",
        line=dict(color=THEME_COLORS["warning"], width=INDICATOR_LINE_WIDTH)
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df["bb_mid"],
        name="BB Mid",
        mode="lines",
        line=dict(color=THEME_COLORS["neutral"], width=1.0, dash="dot")
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df["bb_lower"],
        name="BB Lower",
        mode="lines",
        line=dict(color=THEME_COLORS["warning"], width=INDICATOR_LINE_WIDTH)
    ))
    
    # Blackout windows
    for event_date in blackout_dates:
        start = event_date - timedelta(days=days_before)
        end = event_date + timedelta(days=days_after)
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor="red", opacity=0.08,
            line_width=0,
            annotation_text="Blackout",
            annotation_position="top left"
        )
    
    # Trend markers (optional)
    if show_trend and "trend_up" in df.columns:
        up_idx = df.index[df["trend_up"]]
        dn_idx = df.index[df["trend_down"]]
        
        fig.add_trace(go.Scatter(
            x=up_idx, y=df.loc[up_idx, "vwap"],
            name="Uptrend",
            mode="markers",
            marker=dict(color=THEME_COLORS["win"], size=5, opacity=0.5, symbol="triangle-up")
        ))
        
        fig.add_trace(go.Scatter(
            x=dn_idx, y=df.loc[dn_idx, "vwap"],
            name="Downtrend",
            mode="markers",
            marker=dict(color=THEME_COLORS["loss"], size=5, opacity=0.5, symbol="triangle-down")
        ))
    
    # Trade markers
    if not trades_df.empty:
        # Entries
        wins_mask = trades_df["outcome"] == "win"
        losses_mask = trades_df["outcome"] == "loss"
        
        fig.add_trace(go.Scatter(
            x=trades_df.loc[wins_mask, "entry_date"],
            y=df.loc[trades_df.loc[wins_mask, "entry_date"], "vwap"],
            name="Entry (Win)",
            mode="markers",
            marker=dict(symbol="triangle-up", color=THEME_COLORS["win"], size=MARKER_SIZE)
        ))
        
        fig.add_trace(go.Scatter(
            x=trades_df.loc[losses_mask, "entry_date"],
            y=df.loc[trades_df.loc[losses_mask, "entry_date"], "vwap"],
            name="Entry (Loss)",
            mode="markers",
            marker=dict(symbol="triangle-up", color=THEME_COLORS["loss"], size=MARKER_SIZE)
        ))
        
        # Exits
        for outcome, symbol, color in [
            ("win", "x", THEME_COLORS["win"]),
            ("loss", "x", THEME_COLORS["loss"]),
            ("breach", "triangle-down", THEME_COLORS["loss"]),
            ("adx_exit", "square", "purple"),
            ("vwap_exit", "diamond", THEME_COLORS["warning"]),
            ("broke", "star", "black"),
        ]:
            mask = trades_df["outcome"] == outcome
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=trades_df.loc[mask, "expiry_date"],
                    y=df.loc[trades_df.loc[mask, "expiry_date"], "close"],
                    name=f"Exit ({outcome})",
                    mode="markers",
                    marker=dict(symbol=symbol, color=color, size=MARKER_SIZE)
                ))
    
    fig.update_layout(
        template=CHART_TEMPLATE,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Price ($)",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    
    return fig


def create_pnl_distribution(trades_df: pd.DataFrame, bins: int = 30) -> go.Figure:
    """Create P&L distribution histogram."""
    fig = go.Figure()
    
    if not trades_df.empty and "pnl" in trades_df.columns:
        pnl = trades_df["pnl"]
        
        fig.add_trace(go.Histogram(
            x=pnl,
            nbinsx=bins,
            name="P&L Distribution",
            marker=dict(
                color=pnl,
                colorscale=[[0, THEME_COLORS["loss"]], [0.5, THEME_COLORS["neutral"]], [1, THEME_COLORS["win"]]],
                line=dict(color=THEME_COLORS["text"], width=1)
            )
        ))
        
        # Add mean line
        mean_pnl = pnl.mean()
        fig.add_vline(
            x=mean_pnl,
            line=dict(color=THEME_COLORS["secondary"], width=2, dash="dash"),
            annotation_text=f"Mean: ${mean_pnl:.2f}",
            annotation_position="top"
        )
    
    fig.update_layout(
        template=CHART_TEMPLATE,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
        showlegend=False
    )
    
    return fig
