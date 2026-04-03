#!/bin/bash

# Pharmacy Demand Forecasting - Database Setup Script

echo "================================================"
echo "Database Setup for Pharmacy Forecasting System"
echo "================================================"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL first:"
    echo "   brew install postgresql@14"
    echo "   brew services start postgresql@14"
    exit 1
fi

echo "✓ PostgreSQL found"
echo ""

# Get database connection details
read -p "Enter PostgreSQL username [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "Enter PostgreSQL password: " DB_PASS
echo ""

read -p "Enter database name [pharmacydb]: " DB_NAME
DB_NAME=${DB_NAME:-pharmacydb}

read -p "Enter host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Enter port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

echo ""
echo "Testing connection..."

# Test connection
export PGPASSWORD="$DB_PASS"
if psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "SELECT 1" &> /dev/null; then
    echo "✓ Connection successful"
else
    echo "❌ Connection failed. Please check your credentials."
    exit 1
fi

# Check if database exists
DB_EXISTS=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" = "1" ]; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "CREATE DATABASE $DB_NAME"
    echo "✓ Database created"
fi

# Apply schema
echo ""
echo "Applying database schema..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f db/schema.sql

if [ $? -eq 0 ]; then
    echo "✓ Schema applied successfully"
else
    echo "❌ Failed to apply schema"
    exit 1
fi

# Update .env file
echo ""
echo "Updating .env files..."
DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"

# Create .env in project root
cat > .env << EOF
# Database Configuration
DATABASE_URL=$DATABASE_URL

# ML Pipeline Configuration
RAW_DATA_CSV_PATH=./salesdaily.csv

# Optional: Model Configuration
FORECAST_HORIZON_DAYS=30
EOF

# Create .env in web directory for Next.js
cat > web/.env << EOF
# Database Configuration
DATABASE_URL=$DATABASE_URL
EOF

echo "✓ .env files created (root and web/)"

echo ""
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "You can now run the ML pipeline:"
echo "  cd ml"
echo "  source venv/bin/activate"
echo "  python cli.py run_pipeline"
echo ""
