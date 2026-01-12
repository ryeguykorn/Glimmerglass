"""Configuration constants for Iron Condor Backtester."""

from typing import Dict, Set

# Application Metadata
APP_TITLE = "Iron Condor Backtester"
APP_ICON = "📈"
VERSION = "2.0.0"

# CSV Schema
REQUIRED_COLUMNS: Set[str] = {"timestamp", "open", "high", "low", "close", "vwap"}
OPTIONAL_COLUMNS: Set[str] = {"volume"}

COLUMN_DTYPES: Dict[str, str] = {
    "timestamp": "datetime64[ns]",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "vwap": "float64",
    "volume": "float64",
}

# Timeframe Mappings
TIMEFRAME_TO_FREQ: Dict[str, str] = {
    "Daily": "D",
    "Hourly": "H",
    "30-minute": "30min",
    "15-minute": "15min",
    "5-minute": "5min",
    "1-minute": "T",
}

TIMEFRAME_BB_MULTIPLIERS: Dict[str, float] = {
    "Daily": 1.0,
    "Hourly": 6.5,
    "30-minute": 13.0,
    "15-minute": 26.0,
    "5-minute": 78.0,
    "1-minute": 390.0,
}

TIMEFRAME_OPTIONS = [
    "Daily",
    "Hourly",
    "30-minute",
    "15-minute",
    "5-minute",
    "1-minute",
]

# Trading Constants
PER_LEG_FEE = 0.65
CONTRACT_MULTIPLIER = 100
DEFAULT_WING_WIDTH = 5.0
DEFAULT_CREDIT_MULTIPLIER = 0.30

# Indicator Defaults
RSI_PERIOD = 14
ADX_PERIOD = 14
BB_BASE_WINDOW = 20
HV_WINDOW = 21
VWAP_SMA_WINDOW = 20
BB_STD_MULTIPLIER = 2.0
BB_TIGHTENING_WINDOW = 20
ANNUALIZATION_FACTOR = 252  # Trading days per year

# Backtest Defaults
DEFAULT_HV_MIN = 15.0
DEFAULT_HV_MAX = 40.0
DEFAULT_ADX_EXIT = 30
DEFAULT_VWAP_K = 1.0
DEFAULT_TREND_METHOD = "VWAP Slope"
DEFAULT_BIAS_STRENGTH = 2.0
DEFAULT_WING_EXT_PCT = 20.0
DEFAULT_DAYS_BEFORE = 7
DEFAULT_DAYS_AFTER = 1

# Entry Filters
ADX_ENTRY_THRESHOLD = 20
RSI_LOWER_BOUND = 40
RSI_UPPER_BOUND = 60

# UI Theme (Terminal Finance)
THEME_COLORS = {
    "background": "#0E1117",
    "surface": "#1E2329",
    "primary": "#00FF41",  # Matrix green
    "secondary": "#00D9FF",  # Cyan
    "warning": "#FFB800",  # Amber
    "error": "#FF4B4B",  # Red
    "win": "#00FF41",
    "loss": "#FF4B4B",
    "neutral": "#64748B",
    "text": "#FAFAFA",
    "text_dim": "#94A3B8",
}

# Chart Settings
CHART_HEIGHT = 500
CHART_TEMPLATE = "plotly_dark"
EQUITY_LINE_WIDTH = 3
INDICATOR_LINE_WIDTH = 1.5
MARKER_SIZE = 9

# Performance Settings
MAX_CACHE_ENTRIES = 5
MAX_TABLE_ROWS = 1000
PROGRESS_UPDATE_INTERVAL = 0.05  # Update every 5%

# Export Settings
EXPORT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
EXPORT_DATE_FORMAT = "%Y-%m-%d"
