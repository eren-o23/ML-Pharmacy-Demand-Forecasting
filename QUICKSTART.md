# Quick Start Guide

## ✅ What's Working

Your system has successfully:
- ✅ Loaded 2,106 rows from `salesdaily.csv`
- ✅ Transformed to 16,848 daily sales records for 8 drugs
- ✅ Date range: 2014-01-02 to 2019-10-08
- ✅ Engineered 24 time-series features

## 🔧 Next Steps: Database Setup

You need to configure PostgreSQL connection. Choose one of these options:

### Option 1: Automated Setup (Recommended)

Run the setup script from the project root:

```bash
cd /Users/erenosman/ml-pharma-project
./setup_database.sh
```

This will:
1. Check PostgreSQL installation
2. Prompt for your credentials
3. Create the database
4. Apply the schema
5. Update your `.env` file automatically

### Option 2: Manual Setup

1. **Create Database:**
   ```bash
   createdb pharmacydb
   ```

2. **Apply Schema:**
   ```bash
   psql -d pharmacydb -f /Users/erenosman/ml-pharma-project/db/schema.sql
   ```

3. **Update `.env` files:**
   
   Create/edit `/Users/erenosman/ml-pharma-project/.env`:
   ```env
   DATABASE_URL=postgresql://YOUR_USERNAME:YOUR_PASSWORD@localhost:5432/pharmacydb
   RAW_DATA_CSV_PATH=./salesdaily.csv
   FORECAST_HORIZON_DAYS=30
   ```
   
   Also create `/Users/erenosman/ml-pharma-project/web/.env`:
   ```env
   DATABASE_URL=postgresql://YOUR_USERNAME:YOUR_PASSWORD@localhost:5432/pharmacydb
   ```
   
   Replace `YOUR_USERNAME` and `YOUR_PASSWORD` with your PostgreSQL credentials.

### Common PostgreSQL Usernames

- **Homebrew installation:** Your Mac username (try `whoami`)
- **PostgreSQL.app:** `postgres`
- **Docker:** `postgres`

### If PostgreSQL is Not Installed

```bash
# Install via Homebrew
brew install postgresql@14
brew services start postgresql@14

# Or use PostgreSQL.app from https://postgresapp.com/
```

## 🚀 Running the Pipeline

Once the database is configured:

```bash
cd ml
source venv/bin/activate
python cli.py run_pipeline
```

Expected output:
```
============================================================
PHARMACY DEMAND FORECASTING PIPELINE
============================================================

[1/8] Loading raw sales data...
[2/8] Transforming to daily sales format...
[3/8] Creating drug metadata...
[4/8] Engineering features...
[5/8] Connecting to database...
[6/8] Training models per drug...
[7/8] Writing forecasts to database...
[8/8] Pipeline complete!
```

## 🌐 Starting the Dashboard

After the pipeline runs successfully:

```bash
cd /Users/erenosman/ml-pharma-project/web
npm install
npx prisma generate
npm run dev
```

Open: http://localhost:3000

## 🐛 Troubleshooting

### "password authentication failed"
- Check your DATABASE_URL in `.env`
- Verify PostgreSQL is running: `pg_isready`
- Try connecting manually: `psql -U YOUR_USERNAME -d pharmacydb`

### "database does not exist"
- Create it: `createdb pharmacydb`
- Or use the setup script

### "No module named 'pandas'"
- Activate virtual environment: `source venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

## 📊 Your Data

Successfully loaded from `ml/salesdaily.csv`:
- **8 drugs:** M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06
- **2,106 days** of sales history
- **Date range:** January 2, 2014 → October 8, 2019

## 🎯 What Happens Next

The pipeline will:
1. Train a LightGBM model for each drug
2. Evaluate on the last 30 days of data
3. Generate 30-day forecasts
4. Store everything in PostgreSQL
5. Make it available in the web dashboard

Estimated runtime: 2-5 minutes depending on your machine.
