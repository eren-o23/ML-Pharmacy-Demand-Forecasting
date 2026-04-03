"""
Shared fixtures for ML pipeline tests.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure ml/ is importable when pytest is run from ml/tests/ directly
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_sales_df() -> pd.DataFrame:
    """120 days of synthetic daily sales for a single drug."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    return pd.DataFrame({
        "date": dates,
        "drug_code": "TEST01",
        "quantity_sold": rng.integers(50, 200, size=120).astype(int),
    })


@pytest.fixture
def feature_df(sample_sales_df) -> pd.DataFrame:
    """Feature-engineered version of sample_sales_df."""
    import feature_engineering
    return feature_engineering.engineer_features(sample_sales_df)
