"""
LightGBM model for demand forecasting.
"""
import logging
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from typing import Tuple, List, Optional
import config

logger = logging.getLogger(__name__)


def save_models(
    drug_code: str,
    model: lgb.Booster,
    lower_model: lgb.Booster,
    upper_model: lgb.Booster,
    model_dir: Path,
) -> None:
    """
    Persist the three models for a drug to disk.

    Files are saved as:
        <model_dir>/<drug_code>_point.lgb
        <model_dir>/<drug_code>_lower.lgb
        <model_dir>/<drug_code>_upper.lgb
    """
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_dir / f"{drug_code}_point.lgb"))
    lower_model.save_model(str(model_dir / f"{drug_code}_lower.lgb"))
    upper_model.save_model(str(model_dir / f"{drug_code}_upper.lgb"))
    logger.info(f"Saved models → {model_dir}/{drug_code}_{{point,lower,upper}}.lgb")


def load_models(
    drug_code: str,
    model_dir: Path,
) -> Tuple[lgb.Booster, lgb.Booster, lgb.Booster]:
    """
    Load persisted models for a drug from disk.

    Raises:
        FileNotFoundError: if any of the three model files are missing.
    """
    paths = {
        'point': model_dir / f"{drug_code}_point.lgb",
        'lower': model_dir / f"{drug_code}_lower.lgb",
        'upper': model_dir / f"{drug_code}_upper.lgb",
    }
    for label, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing saved model ({label}): {path}")

    return (
        lgb.Booster(model_file=str(paths['point'])),
        lgb.Booster(model_file=str(paths['lower'])),
        lgb.Booster(model_file=str(paths['upper'])),
    )


def prepare_train_test_split(
    df: pd.DataFrame, 
    test_days: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data into train and test sets by date.
    
    Args:
        df: Feature-engineered DataFrame
        test_days: Number of days to use for testing
        
    Returns:
        Tuple of (train_df, test_df)
    """
    df = df.sort_values('date')
    split_date = df['date'].max() - pd.Timedelta(days=test_days)
    
    train_df = df[df['date'] <= split_date].copy()
    test_df = df[df['date'] > split_date].copy()
    
    return train_df, test_df


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """
    Get list of feature columns for modeling.
    
    Args:
        df: DataFrame with features
        
    Returns:
        List of feature column names
    """
    exclude_cols = ['date', 'drug_code', 'quantity_sold', 'drug_id']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    return feature_cols


def train_lightgbm_model(
    train_df: pd.DataFrame,
    valid_df: Optional[pd.DataFrame] = None,
    params: Optional[dict] = None,
    verbose: bool = True,
) -> lgb.Booster:
    """
    Train LightGBM model for demand forecasting.

    Args:
        train_df: Training DataFrame with features and target
        valid_df: Optional validation DataFrame
        params: Model hyperparameters (uses config defaults if None)
        verbose: Whether to log training progress. Set False for CV folds
                 to avoid noisy output.

    Returns:
        Trained LightGBM Booster model
    """
    if params is None:
        params = config.LIGHTGBM_PARAMS.copy()

    feature_cols = get_feature_columns(train_df)

    X_train = train_df[feature_cols]
    y_train = train_df['quantity_sold']

    train_data = lgb.Dataset(X_train, label=y_train)

    valid_data = None
    if valid_df is not None:
        X_valid = valid_df[feature_cols]
        y_valid = valid_df['quantity_sold']
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)

    callbacks = [lgb.early_stopping(stopping_rounds=50)]
    if verbose:
        callbacks.append(lgb.log_evaluation(period=100))

    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[train_data, valid_data] if valid_data else [train_data],
        valid_names=['train', 'valid'] if valid_data else ['train'],
        callbacks=callbacks,
    )

    return model


def walk_forward_validate(
    df: pd.DataFrame,
    n_folds: int = 3,
    test_days: int = 30,
) -> dict:
    """
    Evaluate forecast accuracy using walk-forward cross-validation.

    Splits the time series into n_folds consecutive test windows, training on
    all data preceding each window. Averaging metrics across folds gives a less
    optimistic estimate than a single train/test split, since earlier folds have
    less training data and the model is tested at different points in time.

    Args:
        df: Feature-engineered DataFrame for a single drug.
        n_folds: Number of evaluation folds.
        test_days: Length of each test window in days.

    Returns:
        Dict of averaged metrics (MAE, RMSE, MAPE), or {} if there is
        insufficient data for any fold.
    """
    df_sorted = df.sort_values('date').reset_index(drop=True)
    n = len(df_sorted)
    fold_metrics = []

    for fold in range(n_folds, 0, -1):
        test_end = n - (fold - 1) * test_days
        test_start = test_end - test_days

        if test_start < config.MIN_HISTORY_DAYS:
            logger.debug(f"Fold {n_folds - fold + 1}: skipped (insufficient training data)")
            continue

        train_fold = df_sorted.iloc[:test_start]
        test_fold = df_sorted.iloc[test_start:test_end]

        if len(test_fold) == 0:
            continue

        # Use verbose=False to suppress per-fold training output
        model = train_lightgbm_model(train_fold, valid_df=test_fold, verbose=False)
        y_pred, _, _ = predict_lightgbm(model, test_fold)
        fold_metrics.append(evaluate_model(test_fold['quantity_sold'].values, y_pred))

    if not fold_metrics:
        return {}

    return {
        k: float(np.nanmean([m[k] for m in fold_metrics]))
        for k in fold_metrics[0]
    }


def predict_lightgbm(
    model: lgb.Booster,
    df: pd.DataFrame,
    lower_model: Optional[lgb.Booster] = None,
    upper_model: Optional[lgb.Booster] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Generate predictions using trained LightGBM model.

    Prediction intervals are estimated using separate quantile regression
    models (10th and 90th percentile). If not provided, CIs are returned
    as None.

    Args:
        model: Trained LightGBM regression model (point forecast)
        df: DataFrame with features
        lower_model: LightGBM model trained with alpha=0.1 (10th percentile)
        upper_model: LightGBM model trained with alpha=0.9 (90th percentile)

    Returns:
        Tuple of (predictions, lower_ci, upper_ci)
    """
    feature_cols = get_feature_columns(df)
    X = df[feature_cols]

    predictions = model.predict(X)
    predictions = np.maximum(0, predictions)  # Ensure non-negative

    lower_ci = None
    upper_ci = None

    if lower_model is not None and upper_model is not None:
        lower_ci = np.maximum(0, lower_model.predict(X))
        upper_ci = np.maximum(0, upper_model.predict(X))

    return predictions, lower_ci, upper_ci


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Evaluate model performance.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        
    Returns:
        Dictionary of metrics
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    # Avoid division by zero in MAPE
    mask = y_true > 0
    mape = mean_absolute_percentage_error(y_true[mask], y_pred[mask]) if mask.sum() > 0 else np.nan
    
    metrics = {
        'MAE': mae,
        'RMSE': rmse,
        'MAPE': mape
    }
    
    return metrics


def forecast_future(
    model: lgb.Booster,
    last_known_df: pd.DataFrame,
    horizon: int = 30,
    lower_model: Optional[lgb.Booster] = None,
    upper_model: Optional[lgb.Booster] = None,
) -> pd.DataFrame:
    """
    Generate future forecasts using recursive prediction.

    Lag features are updated correctly at every step by maintaining a
    date-indexed value store that combines actual historical values (from
    last_known_df) with accumulated predictions. This means lag_7 on step 8
    correctly uses the step-1 prediction, lag_14 on step 15 uses the step-1
    prediction, and so on — rather than staying stale.

    Args:
        model: Trained regression model (point forecast)
        last_known_df: DataFrame with the last max(lags) rows of actual data,
            used to seed historical lag lookups for early forecast steps.
        horizon: Number of days to forecast
        lower_model: LightGBM model trained with alpha=0.1
        upper_model: LightGBM model trained with alpha=0.9

    Returns:
        DataFrame with columns: date, predicted_demand, lower_ci, upper_ci
    """
    feature_cols = get_feature_columns(last_known_df)

    # Detect which lag columns are present in the feature set
    lag_cols = [c for c in feature_cols if c.startswith('lag_')]
    lags = [int(c.split('_')[1]) for c in lag_cols]

    # Build a date-indexed store of actual historical values.
    # This lets us correctly resolve lag lookups for early forecast steps
    # where the lag date falls before the forecast horizon.
    value_store: dict = {
        pd.Timestamp(row['date']): float(row['quantity_sold'])
        for _, row in last_known_df.iterrows()
    }

    current_row = last_known_df.iloc[-1:].copy()
    last_date = pd.Timestamp(current_row['date'].values[0])
    forecasts = []

    for i in range(1, horizon + 1):
        next_date = last_date + pd.Timedelta(days=i)

        # --- Date features (use scalar assignment to avoid chained-indexing warnings) ---
        current_row['date'] = next_date
        current_row['day_of_week'] = next_date.dayofweek
        current_row['day_of_month'] = next_date.day
        current_row['month'] = next_date.month
        current_row['quarter'] = next_date.quarter
        current_row['week_of_year'] = next_date.isocalendar()[1]
        current_row['is_weekend'] = int(next_date.dayofweek in (5, 6))
        current_row['is_month_start'] = int(next_date.is_month_start)
        current_row['is_month_end'] = int(next_date.is_month_end)

        # --- Lag features: look up the correct historical or predicted value ---
        for lag in lags:
            lag_date = next_date - pd.Timedelta(days=lag)
            # value_store holds actuals for past dates and predictions for
            # already-forecast dates; default to 0 if the date is missing.
            current_row[f'lag_{lag}'] = value_store.get(lag_date, 0.0)

        # NOTE: Rolling features (rolling_mean_*, rolling_std_*, etc.) are not
        # updated during recursive forecasting — they carry forward the last
        # known values unchanged. Updating them correctly would require
        # maintaining a rolling buffer of predictions, adding significant
        # complexity. For this dataset and horizon the impact is modest, but
        # it is a known source of forecast degradation beyond ~7 days.

        X = current_row[feature_cols]

        pred = max(0.0, model.predict(X)[0])
        lower_ci = max(0.0, lower_model.predict(X)[0]) if lower_model is not None else None
        upper_ci = max(0.0, upper_model.predict(X)[0]) if upper_model is not None else None

        # Store prediction so future lag lookups can reference it
        value_store[next_date] = pred

        forecasts.append({
            'date': next_date,
            'predicted_demand': pred,
            'lower_ci': lower_ci,
            'upper_ci': upper_ci,
        })

    return pd.DataFrame(forecasts)
