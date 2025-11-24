#!/bin/bash
# Runtime Initialization Script - Phase D
# Initializes PostgreSQL and prepares environment for multi-process orchestration

set -e

echo "=========================================="
echo "Skeldir Runtime Initialization"
echo "Phase D: Replit-Native Runtime Bootstrap"
echo "=========================================="
echo ""

# Configuration
PGDATA="${PGDATA:-$HOME/pgdata}"
PGSOCKET="${PGSOCKET:-$HOME/.s.PGSQL}"
DB_NAME="skeldir_dev"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Configuration:"
echo "  PGDATA: $PGDATA"
echo "  PGSOCKET: $PGSOCKET"
echo "  DB_NAME: $DB_NAME"
echo ""

# Step 1: Create socket directory
echo "[1/5] Creating PostgreSQL socket directory..."
mkdir -p "$PGSOCKET"
echo -e "${GREEN}✓${NC} Socket directory created: $PGSOCKET"
echo ""

# Step 2: Initialize PostgreSQL if needed
if [ ! -d "$PGDATA" ]; then
    echo "[2/5] Initializing PostgreSQL data directory..."
    initdb -D "$PGDATA" --encoding=UTF8 --locale=C
    echo -e "${GREEN}✓${NC} PostgreSQL data directory initialized"
else
    echo "[2/5] PostgreSQL data directory already exists"
    echo -e "${YELLOW}→${NC} Skipping initdb"
fi
echo ""

# Step 3: Start PostgreSQL temporarily to create database
echo "[3/5] Starting PostgreSQL (temporary)..."
pg_ctl -D "$PGDATA" -o "-k $PGSOCKET" -l "$HOME/postgres.log" start
sleep 2

if pg_isready -h "$PGSOCKET" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL started successfully"
else
    echo -e "${RED}✗${NC} PostgreSQL failed to start"
    echo "Check log: $HOME/postgres.log"
    exit 1
fi
echo ""

# Step 4: Create database
echo "[4/5] Creating database: $DB_NAME..."
if psql -h "$PGSOCKET" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    echo -e "${YELLOW}→${NC} Database $DB_NAME already exists"
else
    createdb -h "$PGSOCKET" "$DB_NAME"
    echo -e "${GREEN}✓${NC} Database $DB_NAME created"
fi
echo ""

# Step 5: Stop PostgreSQL (will be managed by Procfile)
echo "[5/5] Stopping PostgreSQL..."
pg_ctl -D "$PGDATA" stop
echo -e "${GREEN}✓${NC} PostgreSQL stopped"
echo ""

echo "=========================================="
echo -e "${GREEN}Runtime Initialization Complete${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip install -r backend/requirements-dev.txt"
echo "  2. Run migrations: alembic upgrade head"
echo "  3. Start services: Use Procfile orchestration"
echo ""

