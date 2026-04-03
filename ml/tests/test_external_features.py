"""
Tests for external_features.py
"""
import numpy as np
import pandas as pd
import pytest

from external_features import add_holiday_features, add_seasonal_features


@pytest.fixture
def date_df() -> pd.DataFrame:
    """DataFrame covering a full year to test seasonal features."""
    return pd.DataFrame({
        "date": pd.date_range("2018-01-01", periods=365, freq="D"),
    })


class TestAddHolidayFeatures:
    def test_column_added(self, date_df):
        result = add_holiday_features(date_df, country="SI")
        assert "is_holiday" in result.columns

    def test_values_are_binary(self, date_df):
        result = add_holiday_features(date_df, country="SI")
        assert set(result["is_holiday"].unique()).issubset({0, 1})

    def test_some_holidays_detected(self, date_df):
        result = add_holiday_features(date_df, country="SI")
        assert result["is_holiday"].sum() > 0

    def test_known_holiday_new_year(self):
        # 2018-01-01 is New Year's Day — a public holiday in virtually all countries
        df = pd.DataFrame({"date": [pd.Timestamp("2018-01-01")]})
        result = add_holiday_features(df, country="SI")
        assert result["is_holiday"].iloc[0] == 1

    def test_known_non_holiday(self):
        # 2018-06-15 is a regular Friday
        df = pd.DataFrame({"date": [pd.Timestamp("2018-06-15")]})
        result = add_holiday_features(df, country="SI")
        assert result["is_holiday"].iloc[0] == 0

    def test_does_not_modify_original(self, date_df):
        original_cols = list(date_df.columns)
        add_holiday_features(date_df, country="SI")
        assert list(date_df.columns) == original_cols


class TestAddSeasonalFeatures:
    def test_columns_added(self, date_df):
        result = add_seasonal_features(date_df)
        assert "flu_season_index" in result.columns
        assert "allergy_season_index" in result.columns

    def test_values_in_range(self, date_df):
        result = add_seasonal_features(date_df)
        assert result["flu_season_index"].between(0, 1).all()
        assert result["allergy_season_index"].between(0, 1).all()

    def test_flu_peaks_in_january(self):
        df = pd.DataFrame({
            "date": [pd.Timestamp("2018-01-15"), pd.Timestamp("2018-07-15")]
        })
        result = add_seasonal_features(df)
        assert result.loc[0, "flu_season_index"] > result.loc[1, "flu_season_index"]

    def test_flu_troughs_in_july(self):
        # July should have the lowest flu index
        df = pd.DataFrame({"date": pd.date_range("2018-01-01", periods=12, freq="MS")})
        result = add_seasonal_features(df)
        july_idx = result[result["date"].dt.month == 7]["flu_season_index"].values[0]
        assert july_idx == pytest.approx(0.0, abs=0.01)

    def test_flu_peaks_at_1_in_january(self):
        df = pd.DataFrame({"date": [pd.Timestamp("2018-01-01")]})
        result = add_seasonal_features(df)
        assert result["flu_season_index"].iloc[0] == pytest.approx(1.0, abs=0.01)

    def test_allergy_peaks_in_april(self):
        df = pd.DataFrame({
            "date": [pd.Timestamp("2018-04-01"), pd.Timestamp("2018-10-01")]
        })
        result = add_seasonal_features(df)
        assert result.loc[0, "allergy_season_index"] > result.loc[1, "allergy_season_index"]

    def test_allergy_peaks_at_1_in_april(self):
        df = pd.DataFrame({"date": [pd.Timestamp("2018-04-01")]})
        result = add_seasonal_features(df)
        assert result["allergy_season_index"].iloc[0] == pytest.approx(1.0, abs=0.01)

    def test_indices_are_out_of_phase(self, date_df):
        # Flu and allergy seasons should not peak at the same time
        result = add_seasonal_features(date_df)
        correlation = result["flu_season_index"].corr(result["allergy_season_index"])
        # They are shifted by ~3 months so correlation should be moderate, not 1.0
        assert abs(correlation) < 0.9
