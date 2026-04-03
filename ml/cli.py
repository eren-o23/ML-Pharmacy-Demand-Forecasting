"""
Command-line interface for the forecasting pipeline.
"""
import sys
import logging
import argparse
from forecasting_pipeline import run_forecasting_pipeline
from db_utils import get_engine, read_sales_from_db
from sqlalchemy import text
import pandas as pd

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logger for the CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_pipeline(retrain: bool = False):
    """Run the full forecasting pipeline."""
    run_forecasting_pipeline(retrain=retrain)


def check_db_connection():
    """Test database connectivity."""
    logger.info("Testing database connection...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful.")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False


def view_sales(drug_code=None):
    """View sales data from database."""
    try:
        engine = get_engine()
        sales_df = read_sales_from_db(engine, drug_code=drug_code)

        if len(sales_df) == 0:
            logger.info("No sales data found in database.")
        else:
            logger.info("Found %d sales records", len(sales_df))
            print(sales_df.head(10).to_string())
            label = f"Summary for {drug_code}" if drug_code else "Overall summary"
            print(f"\n{label}:")
            print(sales_df.describe().to_string())
    except Exception as e:
        logger.error("Error reading sales data: %s", e)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Pharmacy Demand Forecasting CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run_pipeline command
    pipeline_parser = subparsers.add_parser(
        'run_pipeline',
        help='Run the complete forecasting pipeline'
    )
    pipeline_parser.add_argument(
        '--retrain',
        action='store_true',
        help='Force retraining of all models, ignoring any saved artifacts'
    )
    
    # check_db command
    subparsers.add_parser(
        'check_db',
        help='Check database connection'
    )
    
    # view_sales command
    view_parser = subparsers.add_parser(
        'view_sales',
        help='View sales data from database'
    )
    view_parser.add_argument(
        '--drug-code',
        type=str,
        help='Filter by drug code'
    )
    
    args = parser.parse_args()

    _configure_logging()

    if args.command == 'run_pipeline':
        run_pipeline(retrain=args.retrain)
    elif args.command == 'check_db':
        check_db_connection()
    elif args.command == 'view_sales':
        view_sales(drug_code=args.drug_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
