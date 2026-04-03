#!/bin/bash

# Interactive Database Setup for Postgres.app

PSQL="/Applications/Postgres.app/Contents/Versions/18/bin/psql"

echo "================================================"
echo "Database Setup for Pharmacy Forecasting System"
echo "================================================"
echo ""

# Get credentials
echo "PostgreSQL Configuration"
echo "------------------------"
read -p "Enter PostgreSQL username [erenosman]: " DB_USER
DB_USER=${DB_USER:-erenosman}

read -sp "Enter PostgreSQL password (press Enter if none): " DB_PASS
echo ""

read -p "Enter database name [pharmacydb]: " DB_NAME
DB_NAME=${DB_NAME:-pharmacydb}

read -p "Enter port [5000]: " DB_PORT
DB_PORT=${DB_PORT:-5000}

echo ""
echo "Testing connection..."

# Build connection string
if [ -z "$DB_PASS" ]; then
    # No password
    PGPASSWORD="" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -c "SELECT 1" > /dev/null 2>&1
else
    # With password
    PGPASSWORD="$DB_PASS" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -c "SELECT 1" > /dev/null 2>&1
fi

if [ $? -eq 0 ]; then
    echo "✓ Connection successful"
else
    echo "❌ Connection failed. Please check your credentials."
    exit 1
fi

# Check if database exists
echo "Checking if database exists..."
if [ -z "$DB_PASS" ]; then
    DB_EXISTS=$(PGPASSWORD="" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
else
    DB_EXISTS=$(PGPASSWORD="$DB_PASS" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
fi

if [ "$DB_EXISTS" = "1" ]; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    if [ -z "$DB_PASS" ]; then
        PGPASSWORD="" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -c "CREATE DATABASE $DB_NAME"
    else
        PGPASSWORD="$DB_PASS" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d postgres -c "CREATE DATABASE $DB_NAME"
    fi
    echo "✓ Database created"
fi

# Apply schema
echo ""
echo "Applying database schema..."
if [ -z "$DB_PASS" ]; then
    PGPASSWORD="" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d "$DB_NAME" -f db/schema.sql
else
    PGPASSWORD="$DB_PASS" $PSQL -U "$DB_USER" -h localhost -p "$DB_PORT" -d "$DB_NAME" -f db/schema.sql
fi

if [ $? -eq 0 ]; then
    echo "✓ Schema applied successfully"
else
    echo "❌ Failed to apply schema"
    exit 1
fi

# Update .env files
echo ""
echo "Updating .env files..."

if [ -z "$DB_PASS" ]; then
    DATABASE_URL="postgresql://$DB_USER@localhost:$DB_PORT/$DB_NAME"
else
    DATABASE_URL="postgresql://$DB_USER:$DB_PASS@localhost:$DB_PORT/$DB_NAME"
fi

# Create .env in project root
cat > .env << EOF
# Database Configuration
DATABASE_URL=$DATABASE_URL

# ML Pipeline Configuration
RAW_DATA_CSV_PATH=./salesdaily.csv

# Optional: Model Configuration
FORECAST_HORIZON_DAYS=30
EOF

# Create .env in web directory
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
echo "Next steps:"
echo "  1. Test connection:"
echo "     cd ml && source venv/bin/activate && python cli.py check_db"
echo ""
echo "  2. Run ML pipeline:"
echo "     python cli.py run_pipeline"
echo ""
echo "  3. Start dashboard:"
echo "     cd ../web && npm run dev"
echo ""
