"""
Database utilities for interacting with PostgreSQL.
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime
from typing import Optional
import config

logger = logging.getLogger(__name__)

# Module-level engine singleton. SQLAlchemy engines are designed to be
# long-lived objects that manage an internal connection pool. Creating a new
# engine per call would bypass pooling and leak connections.
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Return the shared SQLAlchemy engine, creating it on first call.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(config.DATABASE_URL)
    return _engine


def upsert_drugs(drug_df: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    """
    Upsert drug metadata into drugs table and return DataFrame with database IDs.

    Args:
        drug_df: DataFrame with drug_code, drug_name, atc_code
        engine: SQLAlchemy engine

    Returns:
        DataFrame with additional 'drug_id' column from database
    """
    logger.info(f"Upserting {len(drug_df)} drugs...")

    records = drug_df[['drug_code', 'drug_name', 'atc_code']].to_dict('records')
    upsert_sql = text("""
        INSERT INTO drugs (drug_code, drug_name, atc_code)
        VALUES (:drug_code, :drug_name, :atc_code)
        ON CONFLICT (drug_code)
        DO UPDATE SET
            drug_name = EXCLUDED.drug_name,
            atc_code = EXCLUDED.atc_code
    """)
    with engine.begin() as conn:
        conn.execute(upsert_sql, records)

    with engine.connect() as conn:
        drug_ids = pd.read_sql(
            text("SELECT id as drug_id, drug_code FROM drugs"), conn
        )

    drug_df = drug_df.merge(drug_ids, on='drug_code', how='left')
    logger.info(f"Drug upsert complete. {len(drug_df)} drugs with IDs.")
    return drug_df


def write_sales_daily(sales_df: pd.DataFrame, drug_map: pd.DataFrame, engine: Engine):
    """
    Bulk-upsert daily sales data into sales_daily table.

    Uses a single executemany call rather than one INSERT per row, which is
    significantly faster for large datasets.

    Args:
        sales_df: DataFrame with date, drug_code, quantity_sold
        drug_map: DataFrame with drug_code and drug_id mapping
        engine: SQLAlchemy engine
    """
    logger.info(f"Writing {len(sales_df)} sales records...")

    sales_with_ids = sales_df.merge(
        drug_map[['drug_code', 'drug_id']],
        on='drug_code',
        how='left',
    )
    records = (
        sales_with_ids
        .assign(
            drug_id=lambda df: df['drug_id'].astype(int),
            quantity_sold=lambda df: df['quantity_sold'].astype(int),
        )[['drug_id', 'date', 'quantity_sold']]
        .to_dict('records')
    )

    upsert_sql = text("""
        INSERT INTO sales_daily (drug_id, date, quantity_sold)
        VALUES (:drug_id, :date, :quantity_sold)
        ON CONFLICT (drug_id, date)
        DO UPDATE SET quantity_sold = EXCLUDED.quantity_sold
    """)
    with engine.begin() as conn:
        conn.execute(upsert_sql, records)

    logger.info("Sales data write complete.")


def write_forecasts_daily(
    forecasts_df: pd.DataFrame, 
    drug_map: pd.DataFrame,
    model_name: str,
    engine: Engine,
    run_timestamp: Optional[datetime] = None
):
    """
    Write forecast data to forecasts_daily table.
    
    Args:
        forecasts_df: DataFrame with date, drug_code, predicted_demand, lower_ci, upper_ci
        drug_map: DataFrame with drug_code and drug_id mapping
        model_name: Name of the model that generated forecasts
        engine: SQLAlchemy engine
        run_timestamp: Timestamp of forecast run (defaults to now)
    """
    if run_timestamp is None:
        run_timestamp = datetime.now()
    
    logger.info(f"Writing {len(forecasts_df)} forecast records for model '{model_name}'...")
    
    # Merge to get drug_ids
    forecasts_with_ids = forecasts_df.merge(
        drug_map[['drug_code', 'drug_id']], 
        on='drug_code', 
        how='left'
    )
    
    # Prepare for database
    forecasts_db = forecasts_with_ids[[
        'drug_id', 'date', 'predicted_demand', 'lower_ci', 'upper_ci'
    ]].copy()
    forecasts_db['model_name'] = model_name
    forecasts_db['run_timestamp'] = run_timestamp
    forecasts_db = forecasts_db.rename(columns={'date': 'forecast_date'})
    
    # Write to database
    forecasts_db.to_sql(
        'forecasts_daily',
        engine,
        if_exists='append',
        index=False
    )
    
    logger.info("Forecast write complete.")


def read_sales_from_db(engine: Engine, drug_code: Optional[str] = None) -> pd.DataFrame:
    """
    Read sales data from database.

    Args:
        engine: SQLAlchemy engine
        drug_code: Optional drug code to filter by

    Returns:
        DataFrame with sales data
    """
    if drug_code is not None:
        query = text("""
            SELECT
                d.drug_code,
                d.drug_name,
                s.date,
                s.quantity_sold
            FROM sales_daily s
            JOIN drugs d ON s.drug_id = d.id
            WHERE d.drug_code = :drug_code
            ORDER BY d.drug_code, s.date
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"drug_code": drug_code})
    else:
        query = text("""
            SELECT
                d.drug_code,
                d.drug_name,
                s.date,
                s.quantity_sold
            FROM sales_daily s
            JOIN drugs d ON s.drug_id = d.id
            ORDER BY d.drug_code, s.date
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn)
