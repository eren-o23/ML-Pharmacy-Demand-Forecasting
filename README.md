# Pharmacy Demand Forecasting

A full-stack system for forecasting daily pharmaceutical drug demand. The ML pipeline trains a LightGBM model per drug and evaluates it against three classical baselines using walk-forward cross-validation, producing a quantified answer to whether the ML complexity is justified. Prediction intervals are derived from quantile regression models rather than heuristic estimates.

**Stack:** Python · LightGBM · PostgreSQL · Next.js 14 · TypeScript · Prisma · Tailwind CSS

---

## How it works

### Forecasting approach

Each drug gets three LightGBM models trained on the same feature set:

- **Point forecast** — standard regression model
- **Lower bound** — quantile regression at α = 0.10
- **Upper bound** — quantile regression at α = 0.90

This gives statistically grounded 80% prediction intervals rather than an arbitrary ± band.

Future forecasts are generated recursively. Lag features (`lag_1`, `lag_7`, `lag_14`, `lag_30`) are correctly updated at each step using a date-indexed value store that combines actual history with accumulated predictions.

### Evaluation

All models — LightGBM and the three baselines — are evaluated on the same **walk-forward cross-validation** folds (3 folds, 30-day test windows). Averaging across folds produces a more honest estimate than a single holdout split.

The pipeline logs a per-drug comparison table and an aggregate summary on every run:

```
Overall Walk-forward CV Summary (3 folds, 8 drugs):
  Model              Avg MAE  Avg RMSE  Avg MAPE
  Naive                  3.7       4.7     91.2%
  Moving Average         3.1       4.2     66.4%
  Seasonal Naive         3.8       5.1     89.4%
  LightGBM               2.7       3.5     65.6%  ← best

  LightGBM vs best baseline: +1.2% MAPE improvement
```

The aggregate improvement is modest because results vary significantly by drug. LightGBM outperforms all baselines on 4/8 drugs (e.g. R06: 51.0% vs 71.7% MAPE). The aggregate is pulled down by R03, a respiratory drug where 23% of days have zero sales and the coefficient of variation exceeds 1.0. On zero-inflated, highly erratic series like this, lag and rolling features average across many zero days and can actively mislead the model — the naive forecast wins. The pipeline logs a warning automatically when a drug exceeds 10% zero-fraction.

### Features

| Type | Features |
|---|---|
| Calendar | day of week, month, quarter, week of year, weekend / month-start / month-end flags |
| Lag | 1, 7, 14, 30-day lags |
| Rolling | 7, 14, 30-day mean, std, min, max (shift(1) to prevent leakage) |
| External | `is_holiday` (public holiday indicator, country-configurable via `HOLIDAYS_COUNTRY`), `flu_season_index` (sinusoidal proxy peaking January), `allergy_season_index` (sinusoidal proxy peaking April) |

External features are the only ones baselines cannot access, making the LightGBM comparison a genuine test of what domain signals add beyond historical sales alone.

### Model persistence

Trained models are saved to `ml/saved_models/` as `.lgb` files (three per drug: point, lower, upper). Subsequent pipeline runs load them directly. Use `--retrain` to force a full retrain and overwrite saved artifacts.

---

## Project structure

```
ml-pharma-project/
├── ml/                         # Python ML pipeline
│   ├── models/
│   │   ├── lightgbm_model.py   # Training, quantile models, CV, save/load
│   │   └── baselines.py        # Naive, moving average, seasonal naive + CV
│   ├── tests/                  # pytest unit tests (68 tests, ~1s)
│   ├── saved_models/           # Persisted .lgb artifacts (git-ignored)
│   ├── config.py
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── db_utils.py
│   ├── forecasting_pipeline.py
│   └── cli.py
├── db/
│   └── schema.sql
├── web/                        # Next.js dashboard
│   ├── app/
│   ├── components/
│   └── prisma/
└── .env.example
```

---

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Node.js 18+

### 1. Database

```bash
createdb pharmacydb
psql -d pharmacydb -f db/schema.sql
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/pharmacydb
RAW_DATA_CSV_PATH=./salesdaily.csv
FORECAST_HORIZON_DAYS=30

# Optional
MODEL_SAVE_DIR=./saved_models
```

### 3. Dataset

Place `salesdaily.csv` in `ml/`. Expected format: one date column (`datum` or `date`) and one numeric column per drug code.

```
datum,M01AB,M01AE,N02BA,N02BE,N05B,N05C,R03,R06
2014-01-02,1234,567,890,345,678,234,456,789
```

### 4. Python dependencies

```bash
cd ml
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Web dashboard

```bash
cd web
npm install
npx prisma generate
```

---

## Usage

### ML pipeline

```bash
cd ml

# Run pipeline (loads saved models if available)
python cli.py run_pipeline

# Force full retrain and overwrite saved models
python cli.py run_pipeline --retrain

# Check database connection
python cli.py check_db

# View sales data
python cli.py view_sales
python cli.py view_sales --drug-code M01AB
```

### Web dashboard

```bash
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard shows historical sales and 30-day forecasts with prediction interval bands per drug.

---

## Development

### Running tests

```bash
cd ml
python -m pytest tests/ -v
```

The suite (68 tests) covers feature engineering, external features (holiday detection, seasonal index values and phase), data loading, metric calculations, train/test splitting, and all baseline forecast functions. No database or model training required.

### Adding a new model

1. Create a file in `ml/models/`
2. Implement training and prediction functions
3. Add CV evaluation in `forecasting_pipeline.py` alongside the existing baselines
4. Add tests in `ml/tests/`

---

## Database schema

**`drugs`** — `id`, `drug_code`, `drug_name`, `atc_code`

**`sales_daily`** — `id`, `drug_id`, `date`, `quantity_sold`

**`forecasts_daily`** — `id`, `drug_id`, `forecast_date`, `run_timestamp`, `predicted_demand`, `lower_ci`, `upper_ci`, `model_name`

---

## Deployment

**Pipeline:** Schedule `python cli.py run_pipeline` with cron or Airflow. Use `--retrain` periodically to keep models fresh.

**Dashboard:** `npm run build`, then deploy to Vercel or any Node host. Set `DATABASE_URL` in the environment.

**Database:** Enable connection pooling (PgBouncer recommended) and set up automated backups.

