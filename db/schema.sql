-- Pharmacy Demand Forecasting Database Schema

-- Drugs dimension table
CREATE TABLE IF NOT EXISTS drugs (
    id SERIAL PRIMARY KEY,
    drug_code TEXT UNIQUE NOT NULL,
    drug_name TEXT NOT NULL,
    atc_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drugs_drug_code ON drugs(drug_code);
CREATE INDEX idx_drugs_atc_code ON drugs(atc_code);

-- Daily sales fact table
CREATE TABLE IF NOT EXISTS sales_daily (
    id SERIAL PRIMARY KEY,
    drug_id INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    quantity_sold INTEGER NOT NULL CHECK (quantity_sold >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug_id, date)
);

CREATE INDEX idx_sales_daily_drug_id ON sales_daily(drug_id);
CREATE INDEX idx_sales_daily_date ON sales_daily(date);
CREATE INDEX idx_sales_daily_drug_date ON sales_daily(drug_id, date);

-- Daily forecasts table
CREATE TABLE IF NOT EXISTS forecasts_daily (
    id SERIAL PRIMARY KEY,
    drug_id INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    run_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    predicted_demand NUMERIC(10, 2) NOT NULL,
    lower_ci NUMERIC(10, 2),
    upper_ci NUMERIC(10, 2),
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_forecasts_daily_drug_id ON forecasts_daily(drug_id);
CREATE INDEX idx_forecasts_daily_forecast_date ON forecasts_daily(forecast_date);
CREATE INDEX idx_forecasts_daily_drug_date ON forecasts_daily(drug_id, forecast_date);
CREATE INDEX idx_forecasts_daily_run_timestamp ON forecasts_daily(run_timestamp);

-- View for latest forecasts per drug
CREATE OR REPLACE VIEW latest_forecasts AS
SELECT DISTINCT ON (drug_id, forecast_date)
    id,
    drug_id,
    forecast_date,
    run_timestamp,
    predicted_demand,
    lower_ci,
    upper_ci,
    model_name,
    created_at
FROM forecasts_daily
ORDER BY drug_id, forecast_date, run_timestamp DESC;

-- Comment documentation
COMMENT ON TABLE drugs IS 'Dimension table containing drug master data';
COMMENT ON TABLE sales_daily IS 'Daily historical sales transactions per drug';
COMMENT ON TABLE forecasts_daily IS 'ML-generated demand forecasts with confidence intervals';
COMMENT ON VIEW latest_forecasts IS 'Most recent forecast for each drug and date';
