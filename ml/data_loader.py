"""
Data loader module for pharmacy sales data.
"""
import logging
import pandas as pd
from pathlib import Path
from typing import Tuple
import config

logger = logging.getLogger(__name__)


def load_raw_sales_data() -> pd.DataFrame:
    """
    Load raw sales data from CSV file specified in environment.
    
    Expected CSV columns:
    - datum: date of sale
    - M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06: drug quantities sold
    
    Returns:
        DataFrame with raw sales data
    """
    csv_path = Path(config.RAW_DATA_CSV_PATH)
    
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Sales data CSV not found at {csv_path}. "
            f"Please ensure the file exists or update RAW_DATA_CSV_PATH in .env"
        )
    
    logger.info(f"Loading sales data from {csv_path}...")
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows with columns: {df.columns.tolist()}")
    return df


def aggregate_daily_sales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform wide-format sales data to long-format daily sales per drug.
    
    Args:
        df: Wide-format DataFrame with date column and drug quantity columns
        
    Returns:
        Long-format DataFrame with columns: date, drug_code, quantity_sold
    """
    # Identify date column (usually 'datum' or 'date')
    date_col = None
    for col in ['datum', 'date', 'Date']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        raise ValueError(f"No date column found. Available columns: {df.columns.tolist()}")
    
    # Parse date column
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Get drug columns (exclude date and non-drug columns like Year, Month, Hour, Weekday Name)
    exclude_cols = [date_col, 'Year', 'year', 'Month', 'month', 'Hour', 'hour', 
                    'Weekday Name', 'weekday_name', 'Weekday', 'weekday', 'Day', 'day']
    drug_columns = [col for col in df.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]
    
    # Melt to long format
    df_long = df.melt(
        id_vars=[date_col],
        value_vars=drug_columns,
        var_name='drug_code',
        value_name='quantity_sold'
    )
    
    # Rename date column to standard name
    df_long = df_long.rename(columns={date_col: 'date'})
    
    # Remove rows with missing quantities
    df_long = df_long.dropna(subset=['quantity_sold'])
    
    # Ensure quantity is integer
    df_long['quantity_sold'] = df_long['quantity_sold'].astype(int)
    
    # Sort by drug and date
    df_long = df_long.sort_values(['drug_code', 'date']).reset_index(drop=True)
    
    logger.info(
        f"Aggregated to {len(df_long)} daily sales records "
        f"for {df_long['drug_code'].nunique()} drugs "
        f"({df_long['date'].min().date()} to {df_long['date'].max().date()})"
    )
    return df_long


def create_drug_metadata(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Create drug metadata DataFrame from sales data.
    
    Args:
        df_long: Long-format sales DataFrame
        
    Returns:
        DataFrame with drug_code, drug_name, atc_code
    """
    drugs = df_long['drug_code'].unique()
    
    drug_metadata = pd.DataFrame({
        'drug_code': drugs,
        'drug_name': drugs,  # Use code as name if not available
        'atc_code': drugs    # ATC codes match drug codes in this dataset
    })
    
    return drug_metadata
