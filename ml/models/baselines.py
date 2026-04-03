"""
Baseline forecasting models.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error,
)


def naive_forecast(train_df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """
    Naive forecast: use last observed value as prediction.
    
    Args:
        train_df: Training data with 'date' and 'quantity_sold'
        horizon: Number of days to forecast
        
    Returns:
        DataFrame with forecast dates and predicted values
    """
    last_date = train_df['date'].max()
    last_value = train_df[train_df['date'] == last_date]['quantity_sold'].values[0]
    
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
    
    forecast_df = pd.DataFrame({
        'date': forecast_dates,
        'predicted_demand': last_value,
        'lower_ci': last_value * 0.8,
        'upper_ci': last_value * 1.2
    })
    
    return forecast_df


def moving_average_forecast(
    train_df: pd.DataFrame, 
    window: int = 7, 
    horizon: int = 30
) -> pd.DataFrame:
    """
    Moving average forecast.
    
    Args:
        train_df: Training data with 'date' and 'quantity_sold'
        window: Window size for moving average
        horizon: Number of days to forecast
        
    Returns:
        DataFrame with forecast dates and predicted values
    """
    last_date = train_df['date'].max()
    
    # Calculate moving average from last window days
    recent_data = train_df.nlargest(window, 'date')
    ma_value = recent_data['quantity_sold'].mean()
    ma_std = recent_data['quantity_sold'].std()
    
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
    
    forecast_df = pd.DataFrame({
        'date': forecast_dates,
        'predicted_demand': ma_value,
        'lower_ci': max(0, ma_value - 1.96 * ma_std),
        'upper_ci': ma_value + 1.96 * ma_std
    })
    
    return forecast_df


def seasonal_naive_forecast(
    train_df: pd.DataFrame, 
    season_length: int = 7, 
    horizon: int = 30
) -> pd.DataFrame:
    """
    Seasonal naive forecast: use value from last seasonal period.
    
    Args:
        train_df: Training data with 'date' and 'quantity_sold'
        season_length: Length of seasonal period (e.g., 7 for weekly)
        horizon: Number of days to forecast
        
    Returns:
        DataFrame with forecast dates and predicted values
    """
    last_date = train_df['date'].max()
    
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
    predictions = []
    
    for i, forecast_date in enumerate(forecast_dates):
        # Get value from same day of week/season from last period
        lookback_date = last_date - pd.Timedelta(days=season_length - (i % season_length))
        lookback_value = train_df[train_df['date'] == lookback_date]['quantity_sold']
        
        if len(lookback_value) > 0:
            predictions.append(lookback_value.values[0])
        else:
            # Fallback to mean if lookback date not found
            predictions.append(train_df['quantity_sold'].mean())
    
    pred_array = np.array(predictions)
    std = train_df['quantity_sold'].std()
    
    forecast_df = pd.DataFrame({
        'date': forecast_dates,
        'predicted_demand': pred_array,
        'lower_ci': np.maximum(0, pred_array - 1.96 * std),
        'upper_ci': pred_array + 1.96 * std
    })
    
    return forecast_df


def evaluate_baselines_cv(
    df: pd.DataFrame,
    n_folds: int = 3,
    test_days: int = 30,
) -> Dict[str, dict]:
    """
    Walk-forward cross-validation for all baseline models.

    Uses the same fold structure as walk_forward_validate so baseline and
    LightGBM metrics are directly comparable.

    Args:
        df: DataFrame with 'date' and 'quantity_sold' columns for a single drug.
        n_folds: Number of evaluation folds.
        test_days: Length of each test window in days.

    Returns:
        Dict mapping baseline name to averaged metrics, e.g.
        {"Naive": {"MAE": ..., "RMSE": ..., "MAPE": ...}, ...}
    """
    _BASELINES = [
        ('Naive', naive_forecast, {}),
        ('Moving Average', moving_average_forecast, {}),
        ('Seasonal Naive', seasonal_naive_forecast, {}),
    ]

    df_sorted = (
        df[['date', 'quantity_sold']]
        .sort_values('date')
        .reset_index(drop=True)
    )
    n = len(df_sorted)
    fold_results: Dict[str, list] = {name: [] for name, _, _ in _BASELINES}

    for fold in range(n_folds, 0, -1):
        test_end = n - (fold - 1) * test_days
        test_start = test_end - test_days

        if test_start < 30:  # Need at least some training history
            continue

        train_fold = df_sorted.iloc[:test_start]
        test_fold = df_sorted.iloc[test_start:test_end]

        if len(test_fold) == 0:
            continue

        y_true = test_fold['quantity_sold'].values
        horizon = len(test_fold)

        for name, fn, kwargs in _BASELINES:
            forecast_df = fn(train_fold, horizon=horizon, **kwargs)
            # Positional alignment: baseline generates consecutive daily dates
            # which match the test fold assuming no gaps in the time series.
            y_pred = forecast_df['predicted_demand'].values[:horizon]

            mae = mean_absolute_error(y_true, y_pred)
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            mask = y_true > 0
            mape = (
                float(mean_absolute_percentage_error(y_true[mask], y_pred[mask]))
                if mask.sum() > 0 else float('nan')
            )
            fold_results[name].append({'MAE': mae, 'RMSE': rmse, 'MAPE': mape})

    return {
        name: {
            k: float(np.nanmean([m[k] for m in folds]))
            for k in ('MAE', 'RMSE', 'MAPE')
        }
        for name, folds in fold_results.items()
        if folds
    }
