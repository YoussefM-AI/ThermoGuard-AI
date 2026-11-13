"""
CabinetSense AI - Feature Engineering and Preprocessing Pipeline
Ensures identical feature computation across dataset training, offline evaluation, and live inference.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List

FEATURE_NAMES = [
    "temperature",
    "humidity",
    "delta_temperature",
    "delta_humidity",
    "rolling_temp_avg",
    "rolling_hum_avg"
]

def compute_engineered_features(df: pd.DataFrame, window_size: int = 5) -> pd.DataFrame:
    """
    Computes time-series differential and rolling features from raw temperature & humidity.
    - delta_temperature: 1st difference (instantaneous variation)
    - delta_humidity: 1st difference (instantaneous variation)
    - rolling_temp_avg: rolling mean over window
    - rolling_hum_avg: rolling mean over window
    Handles boundary/missing values via forward-fill and backward-fill safely.
    """
    df = df.copy()

    # Ensure required raw columns exist
    if "temperature" not in df.columns or "humidity" not in df.columns:
        raise ValueError("DataFrame must contain 'temperature' and 'humidity' columns.")

    # Convert to float and sanitize
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")

    # Safe imputation for missing or corrupted sensor readings
    df["temperature"] = df["temperature"].ffill().bfill().fillna(25.0)
    df["humidity"] = df["humidity"].ffill().bfill().fillna(45.0)

    # 1st Difference (Rate of change)
    df["delta_temperature"] = df["temperature"].diff().fillna(0.0)
    df["delta_humidity"] = df["humidity"].diff().fillna(0.0)

    # Rolling window averages
    df["rolling_temp_avg"] = df["temperature"].rolling(window=window_size, min_periods=1).mean()
    df["rolling_hum_avg"] = df["humidity"].rolling(window=window_size, min_periods=1).mean()

    return df

def extract_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts numerical NumPy feature matrix strictly matching FEATURE_NAMES.
    """
    features_df = compute_engineered_features(df)
    X = features_df[FEATURE_NAMES].to_numpy(dtype=np.float32)
    return X, FEATURE_NAMES
