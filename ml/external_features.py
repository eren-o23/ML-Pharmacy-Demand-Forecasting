"""
External feature engineering for demand forecasting.

Adds two categories of features that baselines cannot use but LightGBM can:

1. Public holidays — discrete events that disrupt normal purchasing patterns.
   Sourced from the `holidays` library; country is configurable via config.

2. Seasonal demand indices — smooth sinusoidal proxies for known pharmaceutical
   demand cycles that are not captured by lag/rolling features alone:
   - flu_season_index: peaks in January (winter respiratory illness season)
   - allergy_season_index: peaks in April (spring pollen season)

   These are engineered proxies, not real epidemiological data, but they encode
   well-established seasonal demand patterns for ATC classes R03 and R06.
   LightGBM can learn per-drug weights for each index from the data.
"""
import logging
import numpy as np
import pandas as pd
import holidays as holidays_lib
import config

logger = logging.getLogger(__name__)


def add_holiday_features(
    df: pd.DataFrame,
    country: str = None,
) -> pd.DataFrame:
    """
    Add a binary public holiday indicator.

    Args:
        df: DataFrame with a 'date' column.
        country: ISO 3166-1 alpha-2 country code (e.g. 'SI', 'DE', 'US').
                 Defaults to config.HOLIDAYS_COUNTRY.

    Returns:
        DataFrame with 'is_holiday' column added (1 = public holiday, 0 = not).
    """
    if country is None:
        country = config.HOLIDAYS_COUNTRY

    df = df.copy()

    years = df["date"].dt.year.unique().tolist()
    country_holidays = holidays_lib.country_holidays(country, years=years)

    df["is_holiday"] = df["date"].dt.date.map(
        lambda d: int(d in country_holidays)
    )

    n_holidays = df["is_holiday"].sum()
    logger.debug(
        f"Added holiday features for {country}: "
        f"{n_holidays} holiday days across {len(years)} years."
    )
    return df


def add_seasonal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add sinusoidal seasonal demand indices.

    Both indices are normalised to [0, 1] using a cosine curve so they are
    smooth, continuous, and interpretable. LightGBM learns the per-drug
    weighting automatically.

    flu_season_index:
        Peak = 1.0 in January, trough = 0.0 in July.
        Relevant for: R03 (respiratory), M01A* (NSAIDs), N02B* (paracetamol).

    allergy_season_index:
        Peak = 1.0 in April, trough = 0.0 in October.
        Relevant for: R06 (antihistamines), R03 (pollen-triggered asthma).

    Args:
        df: DataFrame with a 'date' column.

    Returns:
        DataFrame with 'flu_season_index' and 'allergy_season_index' added.
    """
    df = df.copy()
    month = df["date"].dt.month

    # Flu season: cos curve peaking at month 1 (January)
    df["flu_season_index"] = 0.5 + 0.5 * np.cos(
        2 * np.pi * (month - 1) / 12
    )

    # Allergy season: cos curve peaking at month 4 (April)
    df["allergy_season_index"] = 0.5 + 0.5 * np.cos(
        2 * np.pi * (month - 4) / 12
    )

    return df


def add_external_features(
    df: pd.DataFrame,
    country: str = None,
) -> pd.DataFrame:
    """
    Apply all external feature engineering steps.

    Args:
        df: DataFrame with 'date' column.
        country: ISO country code for public holidays.
                 Defaults to config.HOLIDAYS_COUNTRY.

    Returns:
        DataFrame with holiday and seasonal features added.
    """
    df = add_holiday_features(df, country=country)
    df = add_seasonal_features(df)
    return df
