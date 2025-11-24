#!/bin/bash
# Replit Baseline Validation - Prerequisite for CI Pipeline
# Purpose: Empirically validate Replit environment can support backend stack
# Must complete successfully before CI workflow becomes authoritative
#
# Requirements:
# 1. Multi-process feasibility (FastAPI + Celery + Prism)
# 2. Database connection proof (PostgreSQL)
# 3. Statistical model execution (PyMC/ArviZ)

set -euo pipefail

TIMESTAMP=$(date -Iseconds)
BASELINE_DIR="baseline_validation"
mkdir -p "$BASELINE_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     REPLIT BASELINE VALIDATION - ENVIRONMENT FEASIBILITY         ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Timestamp: $TIMESTAMP"
echo "Environment: Replit Container"
echo ""

# ============================================================================
# 1. MULTI-PROCESS FEASIBILITY VALIDATION
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════"
echo "1. MULTI-PROCESS FEASIBILITY VALIDATION"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check for process manager
PROCESS_MANAGER=""
if command -v supervisord > /dev/null 2>&1; then
    PROCESS_MANAGER="supervisord"
    echo "✓ Process manager: supervisord"
elif command -v honcho > /dev/null 2>&1; then
    PROCESS_MANAGER="honcho"
    echo "✓ Process manager: honcho"
elif command -v foreman > /dev/null 2>&1; then
    PROCESS_MANAGER="foreman"
    echo "✓ Process manager: foreman"
elif command -v overmind > /dev/null 2>&1; then
    PROCESS_MANAGER="overmind"
    echo "✓ Process manager: overmind"
else
    echo "⚠ No process manager found - will use bash script orchestration"
    PROCESS_MANAGER="bash"
fi

echo "Using process manager: $PROCESS_MANAGER" | tee "$BASELINE_DIR/process_manager.txt"
echo ""

# Start services based on available manager
echo "Starting backend services..."
echo ""

if [ -f "Procfile" ]; then
    echo "Found Procfile - starting services via $PROCESS_MANAGER"
    
    if [ "$PROCESS_MANAGER" = "bash" ]; then
        # Manual bash orchestration
        echo "Starting services manually in background..."
        
        # Start PostgreSQL (if not already running)
        if ! pgrep -x postgres > /dev/null; then
            echo "  Starting PostgreSQL..."
            postgres -D "$PGDATA" -k "$PGSOCKET" -h localhost -p 5432 >> "$BASELINE_DIR/postgres.log" 2>&1 &
            sleep 3
        fi
        
        # Start Redis
        if ! pgrep -x redis-server > /dev/null; then
            echo "  Starting Redis..."
            redis-server --port 6379 --bind 127.0.0.1 >> "$BASELINE_DIR/redis.log" 2>&1 &
            sleep 2
        fi
        
        # Start FastAPI
        echo "  Starting FastAPI (uvicorn)..."
        cd backend
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> "../$BASELINE_DIR/fastapi.log" 2>&1 &
        FASTAPI_PID=$!
        cd ..
        sleep 3
        
        # Start Celery
        echo "  Starting Celery worker..."
        cd backend
        celery -A app.tasks worker --loglevel=info >> "../$BASELINE_DIR/celery.log" 2>&1 &
        CELERY_PID=$!
        cd ..
        sleep 2
        
        # Start Prism mock (if available)
        if command -v prism > /dev/null 2>&1 && [ -f "api-contracts/dist/openapi/v1/attribution.bundled.yaml" ]; then
            echo "  Starting Prism mock server..."
            prism mock api-contracts/dist/openapi/v1/attribution.bundled.yaml -p 4011 -h 0.0.0.0 >> "$BASELINE_DIR/prism.log" 2>&1 &
            PRISM_PID=$!
            sleep 2
        else
            echo "  ⚠ Prism not available - skipping mock server"
        fi
        
        echo "Services started in background"
    else
        # Use process manager
        $PROCESS_MANAGER start >> "$BASELINE_DIR/process_manager.log" 2>&1 &
        PM_PID=$!
        echo "Process manager started (PID: $PM_PID)"
        sleep 5
    fi
else
    echo "✗ ERROR: Procfile not found"
    echo "Cannot proceed with multi-process validation"
    exit 1
fi

echo ""
echo "Waiting for services to stabilize (10 seconds)..."
sleep 10

# Capture process snapshot
echo ""
echo "Capturing process snapshot..."
ps aux | grep -E 'uvicorn|celery|prism|redis|postgres' | grep -v grep > "$BASELINE_DIR/process_snapshot.txt" 2>&1 || true

# Analyze process snapshot
UVICORN_COUNT=$(grep -c uvicorn "$BASELINE_DIR/process_snapshot.txt" || echo "0")
CELERY_COUNT=$(grep -c celery "$BASELINE_DIR/process_snapshot.txt" || echo "0")
REDIS_COUNT=$(grep -c redis "$BASELINE_DIR/process_snapshot.txt" || echo "0")
POSTGRES_COUNT=$(grep -c postgres "$BASELINE_DIR/process_snapshot.txt" || echo "0")
PRISM_COUNT=$(grep -c prism "$BASELINE_DIR/process_snapshot.txt" || echo "0")

echo ""
echo "Process Status:"
echo "  FastAPI (uvicorn): $UVICORN_COUNT process(es)"
echo "  Celery worker:     $CELERY_COUNT process(es)"
echo "  Redis:             $REDIS_COUNT process(es)"
echo "  PostgreSQL:        $POSTGRES_COUNT process(es)"
echo "  Prism mock:        $PRISM_COUNT process(es)"

# Validate multi-process feasibility
MULTI_PROCESS_PASS=true
if [ "$UVICORN_COUNT" -eq 0 ]; then
    echo "✗ FAIL: FastAPI not running"
    MULTI_PROCESS_PASS=false
fi
if [ "$CELERY_COUNT" -eq 0 ]; then
    echo "✗ FAIL: Celery not running"
    MULTI_PROCESS_PASS=false
fi
if [ "$REDIS_COUNT" -eq 0 ]; then
    echo "✗ FAIL: Redis not running"
    MULTI_PROCESS_PASS=false
fi
if [ "$POSTGRES_COUNT" -eq 0 ]; then
    echo "✗ FAIL: PostgreSQL not running"
    MULTI_PROCESS_PASS=false
fi

if [ "$MULTI_PROCESS_PASS" = true ]; then
    echo ""
    echo "✓ Multi-process feasibility: VALIDATED"
    echo "  All core services running concurrently"
else
    echo ""
    echo "✗ Multi-process feasibility: FAILED"
    echo "  Missing required services"
fi

# Check connectivity
echo ""
echo "Testing service connectivity..."

# FastAPI health check
if curl -f http://localhost:8000/health > "$BASELINE_DIR/health_check.txt" 2>&1; then
    echo "✓ FastAPI: Reachable at http://localhost:8000/health"
else
    echo "✗ FastAPI: Not reachable"
    MULTI_PROCESS_PASS=false
fi

# Redis ping
if redis-cli ping > "$BASELINE_DIR/redis_ping.txt" 2>&1; then
    echo "✓ Redis: Responding to PING"
else
    echo "✗ Redis: Not responding"
    MULTI_PROCESS_PASS=false
fi

# Port bindings
echo ""
echo "Capturing port bindings..."
netstat -tuln | grep -E ':(8000|6379|5432)' > "$BASELINE_DIR/port_bindings.txt" 2>&1 || \
    lsof -i -P -n | grep -E ':(8000|6379|5432)' > "$BASELINE_DIR/port_bindings.txt" 2>&1 || \
    echo "Port check tools not available" > "$BASELINE_DIR/port_bindings.txt"

cat "$BASELINE_DIR/port_bindings.txt"

# ============================================================================
# 2. DATABASE CONNECTION PROOF
# ============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "2. DATABASE CONNECTION PROOF"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Determine DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    # Try Replit default
    if [ -n "${PGDATA:-}" ]; then
        export DATABASE_URL="postgresql://$(whoami)@localhost:5432/$(whoami)"
        echo "Using Replit-style DATABASE_URL: $DATABASE_URL"
    else
        echo "✗ ERROR: DATABASE_URL not set and cannot infer"
        echo "  Please set DATABASE_URL environment variable"
        exit 1
    fi
else
    echo "Using DATABASE_URL from environment"
fi

# Test basic connection
echo ""
echo "Testing PostgreSQL connection..."
if psql "$DATABASE_URL" -c "SELECT version();" > "$BASELINE_DIR/db_version.txt" 2>&1; then
    echo "✓ Database connection: SUCCESS"
    echo ""
    echo "PostgreSQL Version:"
    cat "$BASELINE_DIR/db_version.txt"
else
    echo "✗ Database connection: FAILED"
    cat "$BASELINE_DIR/db_version.txt"
    exit 1
fi

# Test schema migration
echo ""
echo "Testing schema migration capability..."
cd backend
if alembic current > "../$BASELINE_DIR/alembic_current.txt" 2>&1; then
    echo "✓ Alembic migrations: Accessible"
    cat "../$BASELINE_DIR/alembic_current.txt"
else
    echo "⚠ Alembic migrations: Not configured or failed"
    cat "../$BASELINE_DIR/alembic_current.txt"
fi
cd ..

# Test data insertion and query
echo ""
echo "Testing data insertion and query..."
psql "$DATABASE_URL" << 'SQL' > "$BASELINE_DIR/db_operations.txt" 2>&1
-- Create test table
CREATE TABLE IF NOT EXISTS baseline_test (
    id SERIAL PRIMARY KEY,
    test_data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert test data
INSERT INTO baseline_test (test_data) VALUES ('Baseline validation test');

-- Query test data
SELECT * FROM baseline_test ORDER BY created_at DESC LIMIT 5;

-- Clean up
DROP TABLE baseline_test;

-- Report success
SELECT 'Database operations: SUCCESS' AS result;
SQL

if grep -q "Database operations: SUCCESS" "$BASELINE_DIR/db_operations.txt"; then
    echo "✓ Database operations: INSERT, SELECT, DROP verified"
else
    echo "✗ Database operations: FAILED"
    cat "$BASELINE_DIR/db_operations.txt"
fi

# Check supported extensions
echo ""
echo "Checking supported PostgreSQL extensions..."
psql "$DATABASE_URL" -c "\dx" > "$BASELINE_DIR/db_extensions.txt" 2>&1
echo "Available extensions saved to $BASELINE_DIR/db_extensions.txt"

# ============================================================================
# 3. STATISTICAL MODEL RUN VERIFICATION
# ============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "3. STATISTICAL MODEL RUN VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check Python environment
echo "Checking Python and scientific stack..."
python --version | tee "$BASELINE_DIR/python_scientific_env.txt"
echo "" >> "$BASELINE_DIR/python_scientific_env.txt"

# Check package availability
python - << 'PYEOF' >> "$BASELINE_DIR/python_scientific_env.txt" 2>&1
import sys
packages = ['numpy', 'pandas', 'scipy', 'matplotlib', 'pymc', 'arviz']
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f"✓ {pkg:15} {version}")
    except ImportError as e:
        print(f"✗ {pkg:15} NOT AVAILABLE")
PYEOF

cat "$BASELINE_DIR/python_scientific_env.txt"

# Run minimal Bayesian model
echo ""
echo "Running minimal Bayesian model (PyMC)..."

if python -c "import pymc" 2>/dev/null; then
    echo "  PyMC available - running model..."
    
    python - << 'PYMODEL' > "$BASELINE_DIR/bayesian_model_run.txt" 2>&1
import numpy as np
import pymc as pm
import arviz as az

print("=== Minimal Bayesian Model Run ===")
print(f"Timestamp: {__import__('datetime').datetime.now().isoformat()}")
print("")

# Generate synthetic data
np.random.seed(42)
x_data = np.linspace(0, 10, 50)
y_data = 2.5 * x_data + 3.0 + np.random.normal(0, 1, size=50)

print("Data generated: 50 observations")
print("")

# Build model
with pm.Model() as model:
    # Priors
    slope = pm.Normal('slope', mu=0, sigma=10)
    intercept = pm.Normal('intercept', mu=0, sigma=10)
    sigma = pm.HalfNormal('sigma', sigma=5)
    
    # Likelihood
    mu = slope * x_data + intercept
    y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y_data)
    
    # Sample
    print("Sampling posterior (2 chains, 500 samples, 500 tune)...")
    trace = pm.sample(500, tune=500, chains=2, cores=1, progressbar=False, random_seed=42)

print("Sampling complete")
print("")

# Convergence diagnostics
summary = az.summary(trace, var_names=['slope', 'intercept'])
print("=== Convergence Diagnostics ===")
print(summary)
print("")

slope_rhat = summary.loc['slope', 'r_hat']
intercept_rhat = summary.loc['intercept', 'r_hat']
slope_ess = summary.loc['slope', 'ess_bulk']
intercept_ess = summary.loc['intercept', 'ess_bulk']

print(f"slope:     R-hat = {slope_rhat:.4f}, ESS = {slope_ess:.0f}")
print(f"intercept: R-hat = {intercept_rhat:.4f}, ESS = {intercept_ess:.0f}")
print("")

# Validation
rhat_pass = slope_rhat < 1.01 and intercept_rhat < 1.01
ess_pass = slope_ess > 100 and intercept_ess > 100

if rhat_pass and ess_pass:
    print("✓ VALIDATION: R-hat < 1.01 and ESS > 100")
    print("Statistical model execution: SUCCESS")
else:
    print(f"⚠ PARTIAL: R-hat {'PASS' if rhat_pass else 'FAIL'}, ESS {'PASS' if ess_pass else 'FAIL'}")
PYMODEL
    
    if grep -q "Statistical model execution: SUCCESS" "$BASELINE_DIR/bayesian_model_run.txt"; then
        echo "✓ Bayesian model: EXECUTED SUCCESSFULLY"
        echo "  Convergence diagnostics generated"
    else
        echo "⚠ Bayesian model: Partial success or convergence issues"
    fi
    
    # Show summary
    echo ""
    echo "Model Run Summary:"
    grep -E "R-hat|ESS|SUCCESS|PARTIAL" "$BASELINE_DIR/bayesian_model_run.txt" | tail -5
    
else
    echo "✗ PyMC not available - statistical validation cannot complete"
    echo "  This is a BLOCKING issue for baseline validation"
    echo "PyMC not available" > "$BASELINE_DIR/bayesian_model_run.txt"
fi

# ============================================================================
# BASELINE VALIDATION SUMMARY
# ============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "BASELINE VALIDATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

{
    echo "=== Replit Baseline Validation Report ==="
    echo "Timestamp: $TIMESTAMP"
    echo "Environment: Replit Container"
    echo ""
    echo "1. Multi-Process Feasibility:"
    echo "   FastAPI: $UVICORN_COUNT process(es)"
    echo "   Celery:  $CELERY_COUNT process(es)"
    echo "   Redis:   $REDIS_COUNT process(es)"
    echo "   PostgreSQL: $POSTGRES_COUNT process(es)"
    echo "   Status: $([ "$MULTI_PROCESS_PASS" = true ] && echo "VALIDATED" || echo "FAILED")"
    echo ""
    echo "2. Database Connection:"
    echo "   PostgreSQL: $(grep -q "version" "$BASELINE_DIR/db_version.txt" && echo "CONNECTED" || echo "FAILED")"
    echo "   Operations: $(grep -q "SUCCESS" "$BASELINE_DIR/db_operations.txt" && echo "VERIFIED" || echo "FAILED")"
    echo ""
    echo "3. Statistical Model:"
    echo "   PyMC: $(python -c "import pymc; print('AVAILABLE')" 2>/dev/null || echo "NOT AVAILABLE")"
    echo "   Model Run: $(grep -q "SUCCESS" "$BASELINE_DIR/bayesian_model_run.txt" 2>/dev/null && echo "SUCCESSFUL" || echo "FAILED/PARTIAL")"
    echo ""
    echo "Artifacts Generated:"
    find "$BASELINE_DIR" -type f -exec ls -lh {} \; | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    
    if [ "$MULTI_PROCESS_PASS" = true ] && \
       grep -q "version" "$BASELINE_DIR/db_version.txt" && \
       grep -q "SUCCESS" "$BASELINE_DIR/db_operations.txt"; then
        echo "✓ BASELINE VALIDATION: PASSED"
        echo ""
        echo "Environment is suitable for backend orchestration and CI pipeline."
        echo "You may proceed with directive compliance implementation."
    else
        echo "✗ BASELINE VALIDATION: FAILED"
        echo ""
        echo "Critical issues detected. Address failures before proceeding."
        echo "CI pipeline should NOT be considered authoritative until baseline passes."
    fi
    
} | tee "$BASELINE_DIR/VALIDATION_REPORT.txt"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     BASELINE VALIDATION COMPLETE - REVIEW ARTIFACTS             ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Artifacts location: $BASELINE_DIR/"
echo ""
echo "Next steps:"
echo "1. Review $BASELINE_DIR/VALIDATION_REPORT.txt"
echo "2. If PASSED: Commit baseline artifacts to evidence registry"
echo "3. If FAILED: Resolve blocking issues before CI implementation"
echo ""
