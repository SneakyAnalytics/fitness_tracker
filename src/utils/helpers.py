from typing import Any
import pandas as pd

def format_value(value: Any, is_percentage: bool = False) -> str:
    """Format values consistently"""
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        if is_percentage:
            return f"{value:.1f}%"
        return f"{value:.1f}"
    return str(value)

def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safely divide two numbers with fallback to default"""
    try:
        if b == 0 or a is None or b is None:
            return default
        return a / b
    except:
        return default

def clean_float(value: Any) -> float:
    """Clean float values, handling NaN and infinite values"""
    if pd.isna(value) or pd.isnull(value):
        return None
    try:
        float_val = float(value)
        return float_val
    except (ValueError, TypeError):
        return None