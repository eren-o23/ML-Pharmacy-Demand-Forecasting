"""
Tests for model evaluation and splitting utilities in lightgbm_model.py.

Deliberately excludes anything that requires LightGBM training (too slow
for unit tests). That coverage belongs in integration tests.
"""
import numpy as np
import pytest

from models.lightgbm_model import (
    evaluate_model,
    get_feature_columns,
    prepare_train_test_split,
)


class TestEvaluateModel:
    def test_perfect_predictions_give_zero_errors(self):
        y = np.array([10.0, 20.0, 30.0])
        metrics = evaluate_model(y, y)
        assert metrics["MAE"] == pytest.approx(0.0)
        assert metrics["RMSE"] == pytest.approx(0.0)
        assert metrics["MAPE"] == pytest.approx(0.0)

    def test_mae_known_value(self):
        y_true = np.array([100.0, 200.0, 300.0])
        y_pred = np.array([110.0, 190.0, 310.0])
        metrics = evaluate_model(y_true, y_pred)
        # |10| + |10| + |10| / 3 = 10
        assert metrics["MAE"] == pytest.approx(10.0)

    def test_rmse_known_value(self):
        y_true = np.array([0.0, 0.0, 0.0])
        y_pred = np.array([3.0, 4.0, 0.0])
        metrics = evaluate_model(y_true, y_pred)
        # sqrt((9 + 16 + 0) / 3) = sqrt(25/3)
        assert metrics["RMSE"] == pytest.approx(np.sqrt(25 / 3))

    def test_mape_excludes_zero_actuals(self):
        # MAPE should not be NaN when some (but not all) actuals are zero
        y_true = np.array([0.0, 100.0, 200.0])
        y_pred = np.array([10.0, 110.0, 210.0])
        metrics = evaluate_model(y_true, y_pred)
        assert not np.isnan(metrics["MAPE"])

    def test_mape_is_nan_when_all_actuals_are_zero(self):
        y_true = np.array([0.0, 0.0, 0.0])
        y_pred = np.array([1.0, 2.0, 3.0])
        metrics = evaluate_model(y_true, y_pred)
        assert np.isnan(metrics["MAPE"])

    def test_returns_all_metric_keys(self):
        y = np.array([1.0, 2.0, 3.0])
        metrics = evaluate_model(y, y)
        assert set(metrics.keys()) == {"MAE", "RMSE", "MAPE"}


class TestPrepareTrainTestSplit:
    def test_test_set_size(self, feature_df):
        _, test = prepare_train_test_split(feature_df, test_days=30)
        assert len(test) == 30

    def test_train_set_size(self, feature_df):
        train, _ = prepare_train_test_split(feature_df, test_days=30)
        assert len(train) == len(feature_df) - 30

    def test_no_date_overlap(self, feature_df):
        train, test = prepare_train_test_split(feature_df, test_days=30)
        assert train["date"].max() < test["date"].min()

    def test_combined_covers_all_data(self, feature_df):
        train, test = prepare_train_test_split(feature_df, test_days=30)
        assert len(train) + len(test) == len(feature_df)


class TestGetFeatureColumns:
    def test_excludes_non_feature_columns(self, feature_df):
        cols = get_feature_columns(feature_df)
        for excluded in ("date", "drug_code", "quantity_sold"):
            assert excluded not in cols

    def test_returns_non_empty_list(self, feature_df):
        cols = get_feature_columns(feature_df)
        assert len(cols) > 0

    def test_includes_lag_and_rolling_cols(self, feature_df):
        cols = get_feature_columns(feature_df)
        assert any(c.startswith("lag_") for c in cols)
        assert any(c.startswith("rolling_") for c in cols)
