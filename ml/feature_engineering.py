"""
Feature engineering module for demand forecasting.
"""
import logging
import pandas as pd
import numpy as np
from typing import List
import config
import external_features

logger = logging.getLogger(__name__)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based features to DataFrame.
    
    Args:
        df: DataFrame with 'date' column
        
    Returns:
        DataFrame with additional time features
    """
    df = df.copy()
    
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
    df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
    
    return df


def add_lag_features(df: pd.DataFrame, lags: List[int] = None) -> pd.DataFrame:
    """
    Add lagged features for target variable.
    
    Args:
        df: DataFrame with 'drug_code', 'date', and 'quantity_sold'
        lags: List of lag periods (default from config)
        
    Returns:
        DataFrame with lag features
    """
    if lags is None:
        lags = config.LAG_FEATURES
    
    df = df.copy()
    df = df.sort_values(['drug_code', 'date'])
    
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby('drug_code')['quantity_sold'].shift(lag)
    
    return df


def add_rolling_features(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """
    Add rolling window statistics.
    
    Args:
        df: DataFrame with 'drug_code', 'date', and 'quantity_sold'
        windows: List of window sizes (default from config)
        
    Returns:
        DataFrame with rolling features
    """
    if windows is None:
        windows = config.ROLLING_WINDOWS
    
    df = df.copy()
    df = df.sort_values(['drug_code', 'date'])
    
    for window in windows:
        # Rolling mean
        df[f'rolling_mean_{window}'] = (
            df.groupby('drug_code')['quantity_sold']
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )
        
        # Rolling std
        df[f'rolling_std_{window}'] = (
            df.groupby('drug_code')['quantity_sold']
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).std())
        )
        
        # Rolling min/max
        df[f'rolling_min_{window}'] = (
            df.groupby('drug_code')['quantity_sold']
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).min())
        )
        
        df[f'rolling_max_{window}'] = (
            df.groupby('drug_code')['quantity_sold']
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).max())
        )
    
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature engineering steps.
    
    Args:
        df: Raw DataFrame with date, drug_code, quantity_sold
        
    Returns:
        DataFrame with engineered features
    """
    logger.info("Engineering features...")

    # Add time features
    df = add_time_features(df)

    # Add external features (holidays, seasonal indices)
    df = external_features.add_external_features(df)

    # Add lag features
    df = add_lag_features(df)

    # Add rolling features
    df = add_rolling_features(df)

    # Fill remaining NaNs with 0 for numerical stability
    feature_cols = [col for col in df.columns if col not in ['date', 'drug_code', 'quantity_sold']]
    df[feature_cols] = df[feature_cols].fillna(0)

    logger.info(f"Feature engineering complete. Total features: {len(feature_cols)}")

    return df
