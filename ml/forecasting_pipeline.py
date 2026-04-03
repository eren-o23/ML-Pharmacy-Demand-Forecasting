"""
Main forecasting pipeline that orchestrates the entire ML workflow.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict
import config
import data_loader
import feature_engineering
import db_utils
from models.lightgbm_model import (
    prepare_train_test_split,
    train_lightgbm_model,
    predict_lightgbm,
    evaluate_model,
    forecast_future,
    save_models,
    load_models,
    walk_forward_validate,
)
from models.baselines import evaluate_baselines_cv

logger = logging.getLogger(__name__)

# Display order for model comparison tables
_MODEL_ORDER = ['Naive', 'Moving Average', 'Seasonal Naive', 'LightGBM']


def _log_drug_comparison(drug_code: str, all_metrics: dict, n_folds: int) -> None:
    """Log a per-drug model comparison table."""
    best_mape = min(
        m['MAPE'] for m in all_metrics.values() if not np.isnan(m['MAPE'])
    )
    rows = [
        f"    {drug_code} — Walk-forward CV ({n_folds} folds):",
        f"      {'Model':<18} {'MAE':>8} {'RMSE':>8} {'MAPE':>8}",
    ]
    for name in _MODEL_ORDER:
        if name not in all_metrics:
            continue
        m = all_metrics[name]
        marker = '  ← best' if abs(m['MAPE'] - best_mape) < 1e-9 else ''
        rows.append(
            f"      {name:<18} {m['MAE']:>8.1f} {m['RMSE']:>8.1f}"
            f" {m['MAPE']:>8.1%}{marker}"
        )
    logger.info('\n'.join(rows))


def _log_summary(evaluation_results: dict, n_folds: int) -> None:
    """Log an aggregate model comparison table across all drugs."""
    if not evaluation_results:
        return

    # Average each metric per model across all drugs
    agg: dict = {}
    for drug_metrics in evaluation_results.values():
        for model_name, metrics in drug_metrics.items():
            agg.setdefault(model_name, {'MAE': [], 'RMSE': [], 'MAPE': []})
            for k in ('MAE', 'RMSE', 'MAPE'):
                agg[model_name][k].append(metrics[k])

    avg = {
        name: {k: float(np.nanmean(vals)) for k, vals in metric_lists.items()}
        for name, metric_lists in agg.items()
    }

    best_mape = min(m['MAPE'] for m in avg.values())
    rows = [
        f"\nOverall Walk-forward CV Summary"
        f" ({n_folds} folds, {len(evaluation_results)} drugs):",
        f"  {'Model':<18} {'Avg MAE':>9} {'Avg RMSE':>9} {'Avg MAPE':>9}",
    ]
    for name in _MODEL_ORDER:
        if name not in avg:
            continue
        m = avg[name]
        marker = '  ← best' if abs(m['MAPE'] - best_mape) < 1e-9 else ''
        rows.append(
            f"  {name:<18} {m['MAE']:>9.1f} {m['RMSE']:>9.1f}"
            f" {m['MAPE']:>9.1%}{marker}"
        )

    if 'LightGBM' in avg:
        baseline_mapes = [
            avg[n]['MAPE'] for n in ('Naive', 'Moving Average', 'Seasonal Naive')
            if n in avg
        ]
        if baseline_mapes:
            improvement = (min(baseline_mapes) - avg['LightGBM']['MAPE']) / min(baseline_mapes) * 100
            rows.append(
                f"\n  LightGBM vs best baseline: {improvement:+.1f}% MAPE improvement"
            )

    logger.info('\n'.join(rows))


def run_forecasting_pipeline(retrain: bool = False):
    """
    Execute the complete demand forecasting pipeline.

    Args:
        retrain: When True, always retrain models even if saved artifacts exist.
                 When False (default), load saved models when available and only
                 train when no artifact is found for a drug.

    Steps:
    1. Load raw sales data from CSV
    2. Transform to long format
    3. Create drug dimension
    4. Engineer features
    5. Walk-forward cross-validation (evaluation)
    6. Train (or load) per-drug production models
    7. Generate future forecasts
    8. Write results to database
    """
    logger.info("=" * 60)
    logger.info("PHARMACY DEMAND FORECASTING PIPELINE")
    logger.info("=" * 60)

    logger.info("[1/8] Loading raw sales data...")
    raw_df = data_loader.load_raw_sales_data()

    logger.info("[2/8] Transforming to daily sales format...")
    sales_df = data_loader.aggregate_daily_sales(raw_df)

    logger.info("[3/8] Creating drug metadata...")
    drug_metadata = data_loader.create_drug_metadata(sales_df)

    logger.info("[4/8] Engineering features...")
    features_df = feature_engineering.engineer_features(sales_df)
    features_df = features_df.dropna(subset=['lag_30'])

    logger.info("[5/8] Connecting to database...")
    engine = db_utils.get_engine()
    drug_metadata = db_utils.upsert_drugs(drug_metadata, engine)
    db_utils.write_sales_daily(sales_df, drug_metadata, engine)

    logger.info("[6/8] Processing per-drug models...")
    drugs = features_df['drug_code'].unique()

    all_forecasts = []
    evaluation_results = {}

    for i, drug_code in enumerate(drugs, 1):
        logger.info(f"  [{i}/{len(drugs)}] {drug_code}")

        drug_df = features_df[features_df['drug_code'] == drug_code].copy()

        if len(drug_df) < config.MIN_HISTORY_DAYS:
            logger.warning(f"    Skipping {drug_code}: insufficient history ({len(drug_df)} days)")
            continue

        train_df, test_df = prepare_train_test_split(drug_df, test_days=30)

        if len(test_df) == 0:
            logger.warning(f"    Skipping {drug_code}: no test data")
            continue

        # Warn on zero-inflated series. When a large fraction of days have zero
        # sales, lag/rolling features average across many zeros and can mislead
        # the model. MAPE is also unreliable (computed only on non-zero days,
        # so small absolute errors on low-volume days produce large % errors).
        # Simple baselines often outperform ML on such series.
        zero_fraction = (drug_df['quantity_sold'] == 0).mean()
        if zero_fraction > 0.10:
            logger.warning(
                f"    {drug_code}: {zero_fraction:.1%} of days have zero sales "
                f"(CV={drug_df['quantity_sold'].std() / drug_df['quantity_sold'].mean():.2f}). "
                "MAPE may be unreliable; ML may not outperform simple baselines."
            )

        # Walk-forward CV for LightGBM and all baselines (same folds for fair comparison)
        logger.info(f"    Walk-forward CV ({config.CV_FOLDS} folds)...")
        lgbm_metrics = walk_forward_validate(drug_df, n_folds=config.CV_FOLDS, test_days=30)
        baseline_metrics = evaluate_baselines_cv(drug_df, n_folds=config.CV_FOLDS, test_days=30)

        if lgbm_metrics:
            all_metrics = {**baseline_metrics, 'LightGBM': lgbm_metrics}
            evaluation_results[drug_code] = all_metrics
            _log_drug_comparison(drug_code, all_metrics, config.CV_FOLDS)

        # Load saved production models or train from scratch
        model, lower_model, upper_model = None, None, None
        if not retrain:
            try:
                model, lower_model, upper_model = load_models(drug_code, config.MODEL_SAVE_DIR)
                logger.info(f"    Loaded saved models from {config.MODEL_SAVE_DIR}")
            except FileNotFoundError:
                pass

        if model is None:
            logger.info("    Training LightGBM models (point + quantile intervals)...")
            model = train_lightgbm_model(train_df, valid_df=test_df)
            lower_model = train_lightgbm_model(train_df, valid_df=test_df, params=config.LIGHTGBM_PARAMS_LOWER)
            upper_model = train_lightgbm_model(train_df, valid_df=test_df, params=config.LIGHTGBM_PARAMS_UPPER)
            save_models(drug_code, model, lower_model, upper_model, config.MODEL_SAVE_DIR)

        logger.info(f"    Generating {config.FORECAST_HORIZON_DAYS}-day forecast...")
        last_known_data = drug_df.tail(max(config.LAG_FEATURES))
        forecast_df = forecast_future(
            model, last_known_data,
            horizon=config.FORECAST_HORIZON_DAYS,
            lower_model=lower_model,
            upper_model=upper_model,
        )
        forecast_df['drug_code'] = drug_code
        all_forecasts.append(forecast_df)

    logger.info("[7/8] Writing forecasts to database...")
    if all_forecasts:
        forecasts_combined = pd.concat(all_forecasts, ignore_index=True)
        db_utils.write_forecasts_daily(
            forecasts_combined,
            drug_metadata,
            model_name='LightGBM',
            engine=engine,
            run_timestamp=datetime.now(),
        )
    else:
        logger.warning("No forecasts generated.")

    logger.info("[8/8] Pipeline complete!")
    _log_summary(evaluation_results, config.CV_FOLDS)
    logger.info("Total drugs processed: %d", len(evaluation_results))
    logger.info(
        "Total forecasts generated: %d",
        len(all_forecasts) * config.FORECAST_HORIZON_DAYS if all_forecasts else 0,
    )


if __name__ == '__main__':
    run_forecasting_pipeline()
