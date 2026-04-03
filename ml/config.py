"""
Configuration module for ML pipeline.
Loads environment variables and provides configuration constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/pharmacydb')

# Data paths
RAW_DATA_CSV_PATH = os.getenv('RAW_DATA_CSV_PATH', './salesdaily.csv')

# Directory where trained model files are saved/loaded
MODEL_SAVE_DIR = Path(os.getenv('MODEL_SAVE_DIR', str(Path(__file__).parent / 'saved_models')))

# ISO 3166-1 alpha-2 country code for public holiday detection.
# Set to match the country where the pharmacy operates.
HOLIDAYS_COUNTRY = os.getenv('HOLIDAYS_COUNTRY', 'MK')

# Model configuration
FORECAST_HORIZON_DAYS = int(os.getenv('FORECAST_HORIZON_DAYS', '30'))

# Feature engineering parameters
LAG_FEATURES = [1, 7, 14, 30]
ROLLING_WINDOWS = [7, 14, 30]

# Model parameters
LIGHTGBM_PARAMS = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1
}

# Quantile model parameters for prediction intervals
_QUANTILE_BASE = {
    'objective': 'quantile',
    'metric': 'quantile',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1
}

LIGHTGBM_PARAMS_LOWER = {**_QUANTILE_BASE, 'alpha': 0.1}  # 10th percentile
LIGHTGBM_PARAMS_UPPER = {**_QUANTILE_BASE, 'alpha': 0.9}  # 90th percentile

# Validation split
TRAIN_TEST_SPLIT_DATE = None  # Will use last 30 days as test set if None
MIN_HISTORY_DAYS = 90  # Minimum history required to train model
CV_FOLDS = 3  # Number of folds for walk-forward cross-validation
