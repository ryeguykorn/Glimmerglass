"""Data structures for backtesting."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
import numpy as np


@dataclass
class Position:
    """Lightweight position representation using dataclass."""
    
    entry_idx: int
    expiry_idx: int
    short_put: float
    long_put: float
    short_call: float
    long_call: float
    credit: float
    
    def __post_init__(self):
        """Validate position strikes."""
        assert self.long_put < self.short_put < self.short_call < self.long_call, \
            "Invalid strike ordering"
        assert self.credit > 0, "Credit must be positive"


@dataclass
class BacktestResult:
    """Complete backtest results."""
    
    df_indicators: pd.DataFrame
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    rejected: pd.DataFrame
    summary: Dict[str, float]
    
    @property
    def has_trades(self) -> bool:
        """Check if any trades were executed."""
        return not self.trades.empty
    
    @property
    def total_pnl(self) -> float:
        """Get total P&L."""
        return self.summary.get("total_pnl", 0.0)
    
    @property
    def win_rate(self) -> float:
        """Get win rate percentage."""
        return self.summary.get("win_rate", 0.0)
    
    @property
    def max_drawdown(self) -> float:
        """Get maximum drawdown in dollars."""
        return self.summary.get("max_drawdown", 0.0)


@dataclass
class ValidationResult:
    """Result of data validation."""
    
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    missing_columns: set[str]
    row_count: int
    date_range: Optional[tuple[datetime, datetime]] = None
    
    def __str__(self) -> str:
        """Human-readable validation summary."""
        status = "✅ Valid" if self.is_valid else "❌ Invalid"
        parts = [f"{status} ({self.row_count} rows)"]
        
        if self.date_range:
            start, end = self.date_range
            parts.append(f"Range: {start.date()} to {end.date()}")
        
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
            
        return " | ".join(parts)
