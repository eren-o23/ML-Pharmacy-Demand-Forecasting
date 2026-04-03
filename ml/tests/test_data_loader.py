"""
Tests for data_loader.py
"""
import pandas as pd
import pytest

import data_loader


@pytest.fixture
def wide_df():
    """Wide-format sales DataFrame with two drug columns."""
    return pd.DataFrame({
        "datum": pd.date_range("2020-01-01", periods=10, freq="D"),
        "M01AB": range(100, 110),
        "N02BA": range(200, 210),
    })


class TestAggregateDailySales:
    def test_produces_long_format(self, wide_df):
        result = data_loader.aggregate_daily_sales(wide_df)
        assert set(result.columns) >= {"date", "drug_code", "quantity_sold"}

    def test_row_count_is_rows_times_drugs(self, wide_df):
        result = data_loader.aggregate_daily_sales(wide_df)
        # 10 dates × 2 drugs = 20 rows
        assert len(result) == 20

    def test_drug_codes_preserved(self, wide_df):
        result = data_loader.aggregate_daily_sales(wide_df)
        assert set(result["drug_code"].unique()) == {"M01AB", "N02BA"}

    def test_detects_datum_column(self, wide_df):
        result = data_loader.aggregate_daily_sales(wide_df)
        assert "date" in result.columns

    def test_detects_date_column_name(self):
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=5, freq="D"),
            "DrugA": range(5),
        })
        result = data_loader.aggregate_daily_sales(df)
        assert "date" in result.columns
        assert len(result) == 5

    def test_raises_on_missing_date_column(self):
        df = pd.DataFrame({"DrugA": range(5), "DrugB": range(5)})
        with pytest.raises(ValueError, match="No date column found"):
            data_loader.aggregate_daily_sales(df)

    def test_drops_nan_quantities(self):
        import numpy as np
        df = pd.DataFrame({
            "datum": pd.date_range("2020-01-01", periods=3, freq="D"),
            "DrugA": [100, None, 120],
        })
        result = data_loader.aggregate_daily_sales(df)
        assert result["quantity_sold"].isna().sum() == 0
        assert len(result) == 2

    def test_sorted_by_drug_then_date(self, wide_df):
        result = data_loader.aggregate_daily_sales(wide_df)
        for drug in result["drug_code"].unique():
            dates = result[result["drug_code"] == drug]["date"]
            assert dates.is_monotonic_increasing


class TestCreateDrugMetadata:
    def test_expected_columns(self, sample_sales_df):
        result = data_loader.create_drug_metadata(sample_sales_df)
        assert set(result.columns) >= {"drug_code", "drug_name", "atc_code"}

    def test_all_drug_codes_present(self, sample_sales_df):
        result = data_loader.create_drug_metadata(sample_sales_df)
        assert "TEST01" in result["drug_code"].values

    def test_no_duplicate_drug_codes(self, sample_sales_df):
        result = data_loader.create_drug_metadata(sample_sales_df)
        assert result["drug_code"].nunique() == len(result)
