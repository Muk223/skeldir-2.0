#!/bin/bash
# Phase 1 - Runtime Empirical Validation
# Purpose: Prove the real runtime is running and resilient using direct OS tools
# Exit Code: 0 if all checks pass, 1 if any check fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/evidence_registry/runtime"

echo "======================================================================="
echo "Phase 1 - Runtime Empirical Validation"
echo "Timestamp: $(date -Iseconds)"
echo "Validating: FastAPI (uvicorn), Celery, Redis, PostgreSQL"
echo "======================================================================="

# Initialize status tracking
ALL_PASS=true

# Ensure evidence directory exists
mkdir -p "$EVIDENCE_DIR"

# 1.1 Health Probe
echo ""
echo "[1/5] Health Probe - Testing /health endpoint..."
if curl -i http://localhost:8000/health > "$EVIDENCE_DIR/health_probe.txt" 2>&1; then
    if grep -q "200 OK" "$EVIDENCE_DIR/health_probe.txt" && grep -q "healthy" "$EVIDENCE_DIR/health_probe.txt"; then
        echo "✓ PASS: Health endpoint returned 200 OK with 'healthy' status"
        echo "  Evidence: evidence_registry/runtime/health_probe.txt"
    else
        echo "✗ FAIL: Health endpoint response invalid"
        ALL_PASS=false
    fi
else
    echo "✗ FAIL: Could not reach health endpoint (is backend running?)"
    ALL_PASS=false
fi

# 1.2 Process Snapshot
echo ""
echo "[2/5] Process Snapshot - Capturing running processes..."
ps aux | grep -E 'uvicorn|celery|redis|postgres' | grep -v grep > "$EVIDENCE_DIR/process_snapshot.txt" 2>&1 || true

# Check for required processes
REQUIRED_PROCESSES=("uvicorn" "celery" "redis" "postgres")
MISSING_PROCESSES=()

for proc in "${REQUIRED_PROCESSES[@]}"; do
    if grep -qi "$proc" "$EVIDENCE_DIR/process_snapshot.txt"; then
        echo "  ✓ $proc process found"
    else
        echo "  ✗ $proc process NOT found"
        MISSING_PROCESSES+=("$proc")
        ALL_PASS=false
    fi
done

if [ ${#MISSING_PROCESSES[@]} -eq 0 ]; then
    echo "✓ PASS: All required processes running"
else
    echo "✗ FAIL: Missing processes: ${MISSING_PROCESSES[*]}"
fi

echo "  Evidence: evidence_registry/runtime/process_snapshot.txt"

# 1.3 Port Bindings
echo ""
echo "[3/5] Port Bindings - Checking open ports..."

# Try lsof first, fall back to netstat
if command -v lsof > /dev/null 2>&1; then
    lsof -i -P -n | grep -E ':(8000|6379|5432)' > "$EVIDENCE_DIR/open_ports.txt" 2>&1 || echo "No ports found via lsof" > "$EVIDENCE_DIR/open_ports.txt"
    PORT_CHECK_METHOD="lsof"
elif command -v netstat > /dev/null 2>&1; then
    netstat -tuln | grep -E ':(8000|6379|5432)' > "$EVIDENCE_DIR/open_ports.txt" 2>&1 || echo "No ports found via netstat" > "$EVIDENCE_DIR/open_ports.txt"
    PORT_CHECK_METHOD="netstat"
else
    echo "⚠ WARN: Neither lsof nor netstat available, skipping port check"
    echo "Port check tools not available" > "$EVIDENCE_DIR/open_ports.txt"
    PORT_CHECK_METHOD="none"
fi

if [ "$PORT_CHECK_METHOD" != "none" ]; then
    REQUIRED_PORTS=(8000 6379 5432)
    MISSING_PORTS=()
    
    for port in "${REQUIRED_PORTS[@]}"; do
        if grep -q ":$port" "$EVIDENCE_DIR/open_ports.txt"; then
            echo "  ✓ Port $port is listening"
        else
            echo "  ✗ Port $port is NOT listening"
            MISSING_PORTS+=("$port")
            ALL_PASS=false
        fi
    done
    
    if [ ${#MISSING_PORTS[@]} -eq 0 ]; then
        echo "✓ PASS: All required ports listening (8000, 6379, 5432)"
    else
        echo "✗ FAIL: Missing ports: ${MISSING_PORTS[*]}"
    fi
fi

echo "  Evidence: evidence_registry/runtime/open_ports.txt"

# 1.4 Orchestration Resilience (kill/restart test)
echo ""
echo "[4/5] Orchestration Resilience - Testing process recovery..."

# Find uvicorn PID
UVICORN_PID=$(ps aux | grep -i 'uvicorn.*app.main:app' | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$UVICORN_PID" ]; then
    echo "✗ FAIL: Could not find uvicorn process for resilience test"
    echo "uvicorn PID not found - resilience test skipped" > "$EVIDENCE_DIR/init_log.txt"
    ALL_PASS=false
else
    echo "  Found uvicorn process: PID $UVICORN_PID"
    echo "  Killing uvicorn to test orchestration restart..."
    
    # Capture pre-kill timestamp
    echo "=== Orchestration Resilience Test ===" > "$EVIDENCE_DIR/init_log.txt"
    echo "Timestamp: $(date -Iseconds)" >> "$EVIDENCE_DIR/init_log.txt"
    echo "Original uvicorn PID: $UVICORN_PID" >> "$EVIDENCE_DIR/init_log.txt"
    echo "" >> "$EVIDENCE_DIR/init_log.txt"
    
    # Kill uvicorn
    kill "$UVICORN_PID" 2>&1 | tee -a "$EVIDENCE_DIR/init_log.txt" || true
    echo "  Sent SIGTERM to PID $UVICORN_PID"
    echo "Process killed at: $(date -Iseconds)" >> "$EVIDENCE_DIR/init_log.txt"
    
    # Wait for orchestrator to restart (Procfile/supervisor should auto-restart)
    echo "  Waiting 5 seconds for automatic restart..."
    sleep 5
    
    # Check if uvicorn restarted
    NEW_UVICORN_PID=$(ps aux | grep -i 'uvicorn.*app.main:app' | grep -v grep | awk '{print $2}' | head -1)
    
    echo "" >> "$EVIDENCE_DIR/init_log.txt"
    if [ -n "$NEW_UVICORN_PID" ]; then
        if [ "$NEW_UVICORN_PID" != "$UVICORN_PID" ]; then
            echo "  ✓ uvicorn restarted with new PID: $NEW_UVICORN_PID"
            echo "✓ PASS: Orchestration resilience confirmed"
            echo "Restart confirmed at: $(date -Iseconds)" >> "$EVIDENCE_DIR/init_log.txt"
            echo "New uvicorn PID: $NEW_UVICORN_PID" >> "$EVIDENCE_DIR/init_log.txt"
            echo "Restart Status: SUCCESS" >> "$EVIDENCE_DIR/init_log.txt"
        else
            echo "  ⚠ WARN: Same PID detected, possible zombie process"
            echo "Same PID detected: possible issue" >> "$EVIDENCE_DIR/init_log.txt"
        fi
    else
        echo "  ✗ uvicorn did NOT restart automatically"
        echo "✗ FAIL: Orchestration resilience test failed"
        echo "Restart Status: FAILED - uvicorn not found after 5s" >> "$EVIDENCE_DIR/init_log.txt"
        ALL_PASS=false
    fi
    
    # Note: In Replit, manual restart might be required
    echo "" >> "$EVIDENCE_DIR/init_log.txt"
    echo "Note: Replit may require manual restart if Procfile runner not active" >> "$EVIDENCE_DIR/init_log.txt"
fi

echo "  Evidence: evidence_registry/runtime/init_log.txt"

# 1.5 Generate Phase 1 Summary
echo ""
echo "[5/5] Generating Phase 1 exit criteria summary..."

{
    echo "=== Phase 1 Runtime Validation Status ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    echo "Exit Criteria:"
    echo "  1. Health endpoint (/health) returns 200 OK: $(grep -q '200 OK' "$EVIDENCE_DIR/health_probe.txt" 2>/dev/null && echo PASS || echo FAIL)"
    echo "  2. Required processes running (uvicorn, celery, redis, postgres): $([ ${#MISSING_PROCESSES[@]} -eq 0 ] && echo PASS || echo FAIL)"
    echo "  3. Required ports listening (8000, 6379, 5432): $([ "$PORT_CHECK_METHOD" != "none" ] && [ ${#MISSING_PORTS[@]} -eq 0 ] && echo PASS || echo PARTIAL)"
    echo "  4. Orchestration resilience (uvicorn restart): $(grep -q 'Restart Status: SUCCESS' "$EVIDENCE_DIR/init_log.txt" 2>/dev/null && echo PASS || echo FAIL/SKIPPED)"
    echo ""
    echo "Overall Status: $([ "$ALL_PASS" = true ] && echo PASS || echo FAIL)"
    echo ""
    echo "Evidence Files:"
    echo "  - health_probe.txt: HTTP response from /health"
    echo "  - process_snapshot.txt: ps aux output filtered for key processes"
    echo "  - open_ports.txt: Port bindings for 8000, 6379, 5432"
    echo "  - init_log.txt: Orchestration restart test log"
    
} | tee "$EVIDENCE_DIR/phase_1_runtime_status.txt"

echo ""
echo "======================================================================="

if [ "$ALL_PASS" = true ]; then
    echo "✓ Phase 1 PASS - Runtime validation complete"
    echo "  Ready to proceed to Phase 2 (Contract Validation)"
    exit 0
else
    echo "✗ Phase 1 FAIL - Runtime validation incomplete"
    echo "  Fix runtime issues (start missing services, check Procfile)"
    exit 1
fi
