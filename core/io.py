"""Data I/O and validation module."""

import hashlib
import pandas as pd
import streamlit as st
from typing import BinaryIO, List
from datetime import datetime

from config import (
    REQUIRED_COLUMNS,
    COLUMN_DTYPES,
    MAX_CACHE_ENTRIES,
)
from core.types import ValidationResult


def compute_file_hash(file: BinaryIO) -> str:
    """Compute SHA256 hash of uploaded file for caching."""
    file.seek(0)
    file_hash = hashlib.sha256(file.read()).hexdigest()[:16]
    file.seek(0)
    return file_hash


@st.cache_data(show_spinner=False, max_entries=MAX_CACHE_ENTRIES)
def load_csv_data(file: BinaryIO, file_hash: str) -> pd.DataFrame:
    """
    Load CSV data with caching based on file hash.
    
    Args:
        file: Uploaded file object
        file_hash: Hash of file content for cache key
        
    Returns:
        DataFrame with lowercase column names
        
    Raises:
        ValueError: If file cannot be parsed
    """
    try:
        df = pd.read_csv(file)
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")


@st.cache_data(show_spinner=False, max_entries=MAX_CACHE_ENTRIES)
def parse_blackout_dates(file: BinaryIO, file_hash: str) -> List[pd.Timestamp]:
    """
    Parse blackout dates from text file.
    
    Format: One date per line (YYYY-MM-DD). Lines starting with '#' are ignored.
    
    Args:
        file: Uploaded text file
        file_hash: Hash of file content for cache key
        
    Returns:
        List of normalized timestamps
    """
    if not file:
        return []
    
    file.seek(0)
    raw = file.read()
    
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    
    blackout_dates = []
    for line_num, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue
        
        try:
            date = pd.Timestamp(pd.to_datetime(stripped)).normalize()
            blackout_dates.append(date)
        except Exception:
            # Silently skip invalid dates (user may have mixed formats)
            pass
    
    return blackout_dates


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """
    Validate uploaded DataFrame against schema requirements.
    
    Checks:
    - Required columns present
    - Data types convertible
    - No all-NaN columns
    - Timestamp parseable
    - High >= Low integrity
    - Minimum row count
    
    Args:
        df: DataFrame to validate
        
    Returns:
        ValidationResult with status and messages
    """
    errors = []
    warnings = []
    
    # Check required columns
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            missing_columns=missing_cols,
            row_count=len(df),
        )
    
    # Check minimum rows
    if len(df) < 100:
        errors.append(f"Insufficient data: {len(df)} rows (minimum 100 required)")
    
    # Validate timestamp
    try:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        if ts.isna().any():
            invalid_count = ts.isna().sum()
            warnings.append(f"{invalid_count} invalid timestamps will be dropped")
        
        valid_ts = ts.dropna()
        if len(valid_ts) > 0:
            date_range = (valid_ts.min().to_pydatetime(), valid_ts.max().to_pydatetime())
        else:
            date_range = None
            errors.append("No valid timestamps found")
    except Exception as e:
        errors.append(f"Timestamp parsing failed: {str(e)}")
        date_range = None
    
    # Check for duplicates
    if "timestamp" in df.columns:
        dup_count = df["timestamp"].duplicated().sum()
        if dup_count > 0:
            warnings.append(f"{dup_count} duplicate timestamps will be deduplicated")
    
    # Validate OHLC integrity
    for col in ["open", "high", "low", "close", "vwap"]:
        if col in df.columns:
            if df[col].isna().all():
                errors.append(f"Column '{col}' contains all NaN values")
            elif df[col].isna().any():
                na_count = df[col].isna().sum()
                warnings.append(f"Column '{col}' has {na_count} missing values")
    
    # Check high >= low
    if "high" in df.columns and "low" in df.columns:
        invalid_bars = (df["high"] < df["low"]).sum()
        if invalid_bars > 0:
            warnings.append(f"{invalid_bars} bars have HIGH < LOW (will be corrected)")
    
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        missing_columns=missing_cols,
        row_count=len(df),
        date_range=date_range,
    )


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare DataFrame for analysis.
    
    Operations:
    - Convert timestamp to datetime
    - Remove duplicates
    - Drop rows with missing required fields
    - Ensure high >= low
    - Sort by timestamp
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    # Convert timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    # Drop invalid timestamps
    df = df.dropna(subset=["timestamp"])
    
    # Remove duplicates (keep first)
    df = df.drop_duplicates(subset=["timestamp"], keep="first")
    
    # Drop rows with missing OHLC or VWAP
    required_for_calc = ["open", "high", "low", "close", "vwap"]
    df = df.dropna(subset=required_for_calc)
    
    # Ensure high >= low
    df.loc[df["high"] < df["low"], ["high", "low"]] = \
        df.loc[df["high"] < df["low"], ["low", "high"]].values
    
    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df
