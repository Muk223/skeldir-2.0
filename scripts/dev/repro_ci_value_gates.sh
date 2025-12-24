#!/usr/bin/env bash
#
# CI-like reproduction harness for VALUE gates (local debugging only).
#
# This script reproduces the GitHub Actions environment locally using Docker Postgres.
# Use this for fast inner-loop debugging. CI is still the source of truth.
#
# Usage:
#   ./scripts/dev/repro_ci_value_gates.sh VALUE_01
#   ./scripts/dev/repro_ci_value_gates.sh VALUE_03
#   ./scripts/dev/repro_ci_value_gates.sh VALUE_05

set -euo pipefail

GATE_ID="${1:-VALUE_01}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/backend/validation/evidence/local_repro"
mkdir -p "$EVIDENCE_DIR"

LOG_FILE="$EVIDENCE_DIR/${GATE_ID}_$(date +%Y%m%d_%H%M%S).log"

echo "=== CI Reproduction Harness for $GATE_ID ===" | tee "$LOG_FILE"
echo "Repo root: $REPO_ROOT" | tee -a "$LOG_FILE"
echo "Evidence dir: $EVIDENCE_DIR" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 1: Start Postgres in Docker (if not already running)
echo "[1/6] Starting Postgres in Docker..." | tee -a "$LOG_FILE"
if ! docker ps | grep -q skeldir-postgres-test; then
    echo "  Starting new Postgres container..." | tee -a "$LOG_FILE"
    docker run --name skeldir-postgres-test \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=postgres \
        -p 5433:5432 \
        -d postgres:15-alpine | tee -a "$LOG_FILE"

    echo "  Waiting for Postgres to be ready..." | tee -a "$LOG_FILE"
    sleep 5
else
    echo "  Postgres already running" | tee -a "$LOG_FILE"
fi

# Step 2: Setup database and roles (same as CI)
echo "[2/6] Setting up database and roles..." | tee -a "$LOG_FILE"
export PGPASSWORD=postgres
psql -h localhost -p 5433 -U postgres <<SQL 2>&1 | tee -a "$LOG_FILE"
DROP DATABASE IF EXISTS skeldir_phase;
DROP ROLE IF EXISTS app_user;
DROP ROLE IF EXISTS app_rw;
DROP ROLE IF EXISTS app_ro;

CREATE USER app_user WITH PASSWORD 'app_user';
CREATE ROLE app_rw NOLOGIN;
CREATE ROLE app_ro NOLOGIN;
CREATE DATABASE skeldir_phase OWNER app_user;

GRANT ALL ON SCHEMA public TO app_user;
GRANT app_rw TO app_user;
GRANT app_ro TO app_user;

\c skeldir_phase
GRANT ALL ON SCHEMA public TO app_user;
SQL

# Step 3: Set environment variables (same as CI)
echo "[3/6] Setting environment variables..." | tee -a "$LOG_FILE"
export DATABASE_URL="postgresql://app_user:app_user@localhost:5433/skeldir_phase"
export MIGRATION_DATABASE_URL="postgresql://app_user:app_user@localhost:5433/skeldir_phase"
export PYTHONPATH="$REPO_ROOT"
export CI="true"

echo "  DATABASE_URL=${DATABASE_URL}" | tee -a "$LOG_FILE"
echo "  PYTHONPATH=${PYTHONPATH}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 4: Run migrations (same as gate runners)
echo "[4/6] Running migrations..." | tee -a "$LOG_FILE"
cd "$REPO_ROOT"
echo "  Working directory: $(pwd)" | tee -a "$LOG_FILE"

alembic upgrade 202511131121 2>&1 | tee -a "$LOG_FILE"
alembic upgrade skeldir_foundation@head 2>&1 | tee -a "$LOG_FILE"
alembic upgrade head 2>&1 | tee -a "$LOG_FILE"

echo "  Verifying alembic current..." | tee -a "$LOG_FILE"
alembic current 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 5: Verify contract bundle exists (for VALUE_03)
if [ "$GATE_ID" = "VALUE_03" ]; then
    echo "[5/6] Verifying contract bundle exists..." | tee -a "$LOG_FILE"
    BUNDLE_PATH="$REPO_ROOT/api-contracts/dist/openapi/v1/llm-explanations.bundled.yaml"
    if [ -f "$BUNDLE_PATH" ]; then
        echo "  ✓ Contract bundle exists: $BUNDLE_PATH" | tee -a "$LOG_FILE"
    else
        echo "  ✗ Contract bundle MISSING: $BUNDLE_PATH" | tee -a "$LOG_FILE"
        echo "  This will cause VALUE_03 test to fail!" | tee -a "$LOG_FILE"
    fi
    echo "" | tee -a "$LOG_FILE"
else
    echo "[5/6] Skipping contract bundle check (not VALUE_03)" | tee -a "$LOG_FILE"
fi

# Step 6: Run pytest (same as gate runners)
echo "[6/6] Running pytest for $GATE_ID..." | tee -a "$LOG_FILE"
TEST_FILE="backend/tests/value_traces/test_value_$(echo $GATE_ID | tr '[:upper:]' '[:lower:]' | cut -d'_' -f2)_*.py"
echo "  Test file pattern: $TEST_FILE" | tee -a "$LOG_FILE"
echo "  Command: python -m pytest $TEST_FILE -v" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

python -m pytest $TEST_FILE -v 2>&1 | tee -a "$LOG_FILE"
TEST_EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ $GATE_ID test PASSED" | tee -a "$LOG_FILE"
else
    echo "✗ $GATE_ID test FAILED (exit code $TEST_EXIT_CODE)" | tee -a "$LOG_FILE"
    echo "  Check log: $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "=== Reproduction complete ===" | tee -a "$LOG_FILE"
echo "Full log: $LOG_FILE" | tee -a "$LOG_FILE"

exit $TEST_EXIT_CODE
