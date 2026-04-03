"""
Tests for models/baselines.py — forecast functions and CV evaluation.
"""
import numpy as np
import pandas as pd
import pytest

from models.baselines import (
    evaluate_baselines_cv,
    moving_average_forecast,
    naive_forecast,
    seasonal_naive_forecast,
)


@pytest.fixture
def train_df(sample_sales_df) -> pd.DataFrame:
    """First 90 rows of the sales fixture as a training set."""
    return (
        sample_sales_df.iloc[:90][["date", "quantity_sold"]]
        .reset_index(drop=True)
    )


class TestNaiveForecast:
    def test_all_predictions_equal_last_value(self, train_df):
        last_val = train_df["quantity_sold"].iloc[-1]
        result = naive_forecast(train_df, horizon=10)
        assert (result["predicted_demand"] == last_val).all()

    def test_correct_number_of_rows(self, train_df):
        result = naive_forecast(train_df, horizon=15)
        assert len(result) == 15

    def test_forecast_starts_day_after_train(self, train_df):
        last_train_date = train_df["date"].max()
        result = naive_forecast(train_df, horizon=5)
        assert result["date"].min() == last_train_date + pd.Timedelta(days=1)

    def test_lower_ci_lte_prediction(self, train_df):
        result = naive_forecast(train_df, horizon=10)
        assert (result["lower_ci"] <= result["predicted_demand"]).all()

    def test_upper_ci_gte_prediction(self, train_df):
        result = naive_forecast(train_df, horizon=10)
        assert (result["upper_ci"] >= result["predicted_demand"]).all()


class TestMovingAverageForecast:
    def test_correct_number_of_rows(self, train_df):
        result = moving_average_forecast(train_df, window=7, horizon=10)
        assert len(result) == 10

    def test_prediction_matches_window_mean(self, train_df):
        window = 7
        result = moving_average_forecast(train_df, window=window, horizon=5)
        expected = train_df.nlargest(window, "date")["quantity_sold"].mean()
        assert result["predicted_demand"].iloc[0] == pytest.approx(expected)

    def test_lower_ci_non_negative(self, train_df):
        result = moving_average_forecast(train_df, window=7, horizon=10)
        assert (result["lower_ci"] >= 0).all()


class TestSeasonalNaiveForecast:
    def test_correct_number_of_rows(self, train_df):
        result = seasonal_naive_forecast(train_df, season_length=7, horizon=14)
        assert len(result) == 14

    def test_lower_ci_non_negative(self, train_df):
        result = seasonal_naive_forecast(train_df, season_length=7, horizon=30)
        assert (result["lower_ci"] >= 0).all()

    def test_fallback_when_lookback_missing(self):
        # Only 3 rows — lookback will be missing for most, forcing mean fallback
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=3, freq="D"),
            "quantity_sold": [100, 120, 110],
        })
        result = seasonal_naive_forecast(df, season_length=7, horizon=5)
        assert len(result) == 5
        assert result["predicted_demand"].notna().all()


class TestEvaluateBaselinesCv:
    def test_returns_all_three_baselines(self, sample_sales_df):
        result = evaluate_baselines_cv(sample_sales_df, n_folds=2, test_days=15)
        assert "Naive" in result
        assert "Moving Average" in result
        assert "Seasonal Naive" in result

    def test_each_result_has_correct_keys(self, sample_sales_df):
        result = evaluate_baselines_cv(sample_sales_df, n_folds=2, test_days=15)
        for metrics in result.values():
            assert set(metrics.keys()) == {"MAE", "RMSE", "MAPE"}

    def test_mae_and_rmse_are_non_negative(self, sample_sales_df):
        result = evaluate_baselines_cv(sample_sales_df, n_folds=2, test_days=15)
        for metrics in result.values():
            assert metrics["MAE"] >= 0
            assert metrics["RMSE"] >= 0

    def test_rmse_gte_mae(self, sample_sales_df):
        # RMSE >= MAE always (Cauchy–Schwarz)
        result = evaluate_baselines_cv(sample_sales_df, n_folds=2, test_days=15)
        for name, metrics in result.items():
            assert metrics["RMSE"] >= metrics["MAE"] - 1e-9, (
                f"{name}: RMSE {metrics['RMSE']:.2f} < MAE {metrics['MAE']:.2f}"
            )

    def test_insufficient_data_returns_empty(self):
        # Only 20 rows — not enough for any fold with test_days=15 and min 30 train rows
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=20, freq="D"),
            "drug_code": "X",
            "quantity_sold": [100] * 20,
        })
        result = evaluate_baselines_cv(df, n_folds=3, test_days=15)
        assert result == {}
