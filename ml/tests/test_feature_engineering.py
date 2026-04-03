"""
Tests for feature_engineering.py
"""
import numpy as np
import pandas as pd
import pytest

import feature_engineering


class TestAddTimeFeatures:
    def test_expected_columns_added(self, sample_sales_df):
        result = feature_engineering.add_time_features(sample_sales_df)
        for col in [
            "day_of_week", "day_of_month", "month", "quarter",
            "week_of_year", "is_weekend", "is_month_start", "is_month_end",
        ]:
            assert col in result.columns, f"Missing column: {col}"

    def test_day_of_week_value(self, sample_sales_df):
        # 2020-01-01 is a Wednesday → dayofweek == 2
        result = feature_engineering.add_time_features(sample_sales_df)
        row = result[result["date"] == pd.Timestamp("2020-01-01")].iloc[0]
        assert row["day_of_week"] == 2

    def test_month_and_day_values(self, sample_sales_df):
        result = feature_engineering.add_time_features(sample_sales_df)
        row = result[result["date"] == pd.Timestamp("2020-01-01")].iloc[0]
        assert row["month"] == 1
        assert row["day_of_month"] == 1

    def test_is_month_start_flag(self, sample_sales_df):
        result = feature_engineering.add_time_features(sample_sales_df)
        row = result[result["date"] == pd.Timestamp("2020-01-01")].iloc[0]
        assert row["is_month_start"] == 1

    def test_is_weekend_flag(self, sample_sales_df):
        result = feature_engineering.add_time_features(sample_sales_df)
        # 2020-01-04 is a Saturday → is_weekend == 1
        sat = result[result["date"] == pd.Timestamp("2020-01-04")].iloc[0]
        assert sat["is_weekend"] == 1
        # 2020-01-01 is a Wednesday → is_weekend == 0
        wed = result[result["date"] == pd.Timestamp("2020-01-01")].iloc[0]
        assert wed["is_weekend"] == 0

    def test_does_not_modify_original(self, sample_sales_df):
        original_cols = list(sample_sales_df.columns)
        feature_engineering.add_time_features(sample_sales_df)
        assert list(sample_sales_df.columns) == original_cols


class TestAddLagFeatures:
    def test_lag_columns_created(self, sample_sales_df):
        result = feature_engineering.add_lag_features(sample_sales_df, lags=[1, 7])
        assert "lag_1" in result.columns
        assert "lag_7" in result.columns

    def test_lag_1_is_previous_value(self, sample_sales_df):
        result = feature_engineering.add_lag_features(
            sample_sales_df, lags=[1]
        ).sort_values("date").reset_index(drop=True)
        # lag_1 at row i == quantity_sold at row i-1
        assert result.loc[5, "lag_1"] == result.loc[4, "quantity_sold"]
        assert result.loc[10, "lag_1"] == result.loc[9, "quantity_sold"]

    def test_first_rows_are_nan(self, sample_sales_df):
        result = feature_engineering.add_lag_features(
            sample_sales_df, lags=[1, 7]
        ).sort_values("date").reset_index(drop=True)
        assert pd.isna(result.loc[0, "lag_1"])
        assert pd.isna(result.loc[6, "lag_7"])


class TestAddRollingFeatures:
    def test_rolling_columns_created(self, sample_sales_df):
        result = feature_engineering.add_rolling_features(sample_sales_df, windows=[7])
        for col in ["rolling_mean_7", "rolling_std_7", "rolling_min_7", "rolling_max_7"]:
            assert col in result.columns

    def test_rolling_mean_bounded(self, sample_sales_df):
        result = feature_engineering.add_rolling_features(
            sample_sales_df, windows=[7]
        ).dropna(subset=["rolling_mean_7"])
        # Rolling mean must be within the range of quantity_sold
        assert (result["rolling_mean_7"] >= result["quantity_sold"].min() * 0.5).all()
        assert (result["rolling_mean_7"] <= result["quantity_sold"].max() * 1.5).all()


class TestEngineerFeatures:
    def test_no_nans_in_feature_columns(self, sample_sales_df):
        result = feature_engineering.engineer_features(sample_sales_df)
        feature_cols = [
            c for c in result.columns
            if c not in ("date", "drug_code", "quantity_sold")
        ]
        assert result[feature_cols].isna().sum().sum() == 0

    def test_quantity_sold_unchanged(self, sample_sales_df):
        result = feature_engineering.engineer_features(sample_sales_df)
        assert (result["quantity_sold"].values == sample_sales_df["quantity_sold"].values).all()

    def test_row_count_unchanged(self, sample_sales_df):
        result = feature_engineering.engineer_features(sample_sales_df)
        assert len(result) == len(sample_sales_df)
