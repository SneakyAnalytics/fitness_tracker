# src/utils/helpers.py

import pandas as pd
import numpy as np
from typing import Any, Optional

def format_value(value: Any, is_percentage: bool = False) -> str:
    """Format a value for display in AI-ready format"""
    if pd.isna(value) or value is None:
        return "N/A"
    
    if isinstance(value, (int, float)):
        if is_percentage:
            return f"{round(float(value), 1)}%"
        return str(round(float(value), 1))
    
    return str(value)

def clean_float(value: Any) -> Optional[float]:
    """Clean float values, handling NaN and infinite values"""
    if pd.isna(value) or pd.isnull(value):
        return None
    if isinstance(value, (int, float)):
        if np.isinf(value) or np.isneginf(value):
            return None
        return float(value)
    return None

def clean_workout_data(data: Any) -> Any:
    """Recursively clean workout data to remove NaN and infinite values"""
    if isinstance(data, dict):
        return {k: clean_workout_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_workout_data(v) for v in data]
    elif isinstance(data, (int, float)):
        if pd.isna(data) or np.isinf(data) or np.isneginf(data):
            return None
        return data
    else:
        return data