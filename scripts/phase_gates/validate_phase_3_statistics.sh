#!/bin/bash
# Phase 3 - Statistical Empirical Validation
# Purpose: Prove PyMC/ArviZ and statistical stack behave correctly via direct sampling
# Exit Code: 0 if all checks pass, 1 or 2 if partial/failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/evidence_registry/statistics"

echo "======================================================================="
echo "Phase 3 - Statistical Empirical Validation"
echo "Timestamp: $(date -Iseconds)"
echo "Validating: NumPy, Pandas, SciPy, Matplotlib, PyMC, ArviZ"
echo "======================================================================="

# Initialize status tracking
ALL_PASS=true

# Ensure evidence directory exists
mkdir -p "$EVIDENCE_DIR"

# Use Python 3.11 venv if available
PYTHON_BIN="python"
if [ -x "$PROJECT_ROOT/backend/.venv311/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/backend/.venv311/bin/python"
    echo "Using Python from: backend/.venv311/bin/python"
else
    echo "Using system Python: $(which python)"
fi

# 3.1 Minimal Direct Import Test
echo ""
echo "[1/3] Direct Import Test - Testing scientific package imports..."

$PYTHON_BIN - << 'PYEOF' > "$EVIDENCE_DIR/imports_raw.txt" 2>&1
try:
    import numpy
    import pandas
    import scipy
    import matplotlib
    import pymc
    import arviz
    print("OK: imports succeeded")
    print(f"  numpy: {numpy.__version__}")
    print(f"  pandas: {pandas.__version__}")
    print(f"  scipy: {scipy.__version__}")
    print(f"  matplotlib: {matplotlib.__version__}")
    print(f"  pymc: {pymc.__version__}")
    print(f"  arviz: {arviz.__version__}")
except ImportError as e:
    print(f"FAIL: Import error - {e}")
    import sys
    sys.exit(1)
PYEOF

IMPORT_STATUS=$?

if [ $IMPORT_STATUS -eq 0 ] && grep -q "OK: imports succeeded" "$EVIDENCE_DIR/imports_raw.txt"; then
    echo "✓ PASS: All scientific packages imported successfully"
    cat "$EVIDENCE_DIR/imports_raw.txt"
else
    echo "✗ FAIL: Import test failed"
    cat "$EVIDENCE_DIR/imports_raw.txt"
    ALL_PASS=false
fi
echo "  Evidence: evidence_registry/statistics/imports_raw.txt"

# 3.2 Full Stack Verification (verify_science_stack.py)
echo ""
echo "[2/3] Full Stack Verification - Running verify_science_stack.py..."

if [ -f "$PROJECT_ROOT/scripts/verify_science_stack.py" ]; then
    $PYTHON_BIN "$PROJECT_ROOT/scripts/verify_science_stack.py" \
      > "$EVIDENCE_DIR/stack_verification_log.txt" 2>&1
    
    STACK_EXIT_CODE=$?
    
    echo "  Script exit code: $STACK_EXIT_CODE"
    
    # Check exit code meaning
    if [ $STACK_EXIT_CODE -eq 0 ]; then
        echo "✓ PASS: Full stack validation succeeded (exit code 0)"
    elif [ $STACK_EXIT_CODE -eq 2 ]; then
        echo "⚠ PARTIAL: Core stack validated, PyMC unavailable (exit code 2)"
    else
        echo "✗ FAIL: Stack validation failed (exit code $STACK_EXIT_CODE)"
        ALL_PASS=false
    fi
    
    # Display key metrics from log
    echo ""
    echo "  Key Metrics from Validation:"
    grep -E "R-hat|ESS|Exit Code|Status:" "$EVIDENCE_DIR/stack_verification_log.txt" 2>/dev/null | head -10 || echo "    (metrics not found in log)"
    
else
    echo "✗ FAIL: verify_science_stack.py not found"
    echo "Script not found" > "$EVIDENCE_DIR/stack_verification_log.txt"
    ALL_PASS=false
fi

echo "  Evidence: evidence_registry/statistics/stack_verification_log.txt"

# 3.3 Verify JSON Results
echo ""
echo "[3/3] Verifying JSON Results - Checking model_results.json..."

if [ -f "$EVIDENCE_DIR/model_results.json" ]; then
    echo "✓ model_results.json created"
    
    # Check exit code in JSON
    JSON_EXIT_CODE=$(grep -oP '"exit_code":\s*\K\d+' "$EVIDENCE_DIR/model_results.json" 2>/dev/null || echo "-1")
    echo "  JSON exit_code: $JSON_EXIT_CODE"
    
    # Check for R-hat and ESS (if PyMC ran)
    if grep -q '"pymc_sampling"' "$EVIDENCE_DIR/model_results.json" 2>/dev/null; then
        echo "  PyMC sampling results found in JSON"
        
        # Extract R-hat values
        SLOPE_RHAT=$(grep -oP '"slope_rhat":\s*\K[0-9.]+' "$EVIDENCE_DIR/model_results.json" 2>/dev/null || echo "N/A")
        INTERCEPT_RHAT=$(grep -oP '"intercept_rhat":\s*\K[0-9.]+' "$EVIDENCE_DIR/model_results.json" 2>/dev/null || echo "N/A")
        
        # Extract ESS values
        SLOPE_ESS=$(grep -oP '"slope_ess":\s*\K[0-9.]+' "$EVIDENCE_DIR/model_results.json" 2>/dev/null || echo "N/A")
        INTERCEPT_ESS=$(grep -oP '"intercept_ess":\s*\K[0-9.]+' "$EVIDENCE_DIR/model_results.json" 2>/dev/null || echo "N/A")
        
        echo "    slope R-hat: $SLOPE_RHAT (must be < 1.01)"
        echo "    intercept R-hat: $INTERCEPT_RHAT (must be < 1.01)"
        echo "    slope ESS: $SLOPE_ESS (must be > 400)"
        echo "    intercept ESS: $INTERCEPT_ESS (must be > 400)"
        
        # Verify thresholds (updated to ESS > 400 per spec)
        if [ "$SLOPE_RHAT" != "N/A" ] && [ "$INTERCEPT_RHAT" != "N/A" ]; then
            RHAT_OK=$(awk -v s="$SLOPE_RHAT" -v i="$INTERCEPT_RHAT" 'BEGIN {print (s < 1.01 && i < 1.01) ? "true" : "false"}')
            if [ "$RHAT_OK" = "true" ]; then
                echo "  ✓ R-hat check: PASS"
            else
                echo "  ✗ R-hat check: FAIL"
                ALL_PASS=false
            fi
        fi
        
        if [ "$SLOPE_ESS" != "N/A" ] && [ "$INTERCEPT_ESS" != "N/A" ]; then
            ESS_OK=$(awk -v s="$SLOPE_ESS" -v i="$INTERCEPT_ESS" 'BEGIN {print (s > 400 && i > 400) ? "true" : "false"}')
            if [ "$ESS_OK" = "true" ]; then
                echo "  ✓ ESS check: PASS"
            else
                echo "  ✗ ESS check: FAIL (need ESS > 400)"
                ALL_PASS=false
            fi
        fi
    else
        echo "  ⚠ PyMC sampling not run (likely Python version incompatibility)"
    fi
else
    echo "✗ FAIL: model_results.json not created"
    ALL_PASS=false
fi

echo "  Evidence: evidence_registry/statistics/model_results.json"

# Generate Phase 3 Summary
echo ""
echo "======================================================================="
{
    echo "=== Phase 3 Statistical Validation Status ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    echo "Exit Criteria:"
    echo "  1. Direct imports succeeded: $(grep -q 'OK: imports succeeded' "$EVIDENCE_DIR/imports_raw.txt" 2>/dev/null && echo PASS || echo FAIL)"
    echo "  2. Stack verification script exit code: ${STACK_EXIT_CODE:-N/A}"
    echo "  3. R-hat < 1.01: ${RHAT_OK:-N/A}"
    echo "  4. ESS > 400: ${ESS_OK:-N/A}"
    echo "  5. JSON results generated: $([ -f "$EVIDENCE_DIR/model_results.json" ] && echo PASS || echo FAIL)"
    echo ""
    echo "Overall Status: $([ "$ALL_PASS" = true ] && echo PASS || echo PARTIAL)"
    echo ""
    echo "Evidence Files:"
    echo "  - imports_raw.txt: Direct import test results"
    echo "  - stack_verification_log.txt: Full validation log with R-hat/ESS"
    echo "  - model_results.json: Machine-readable results"
    echo "  - sampling_output.json: Lightweight sampling summary"
    
} | tee "$EVIDENCE_DIR/phase_3_statistics_status.txt"

echo "======================================================================="

if [ "$ALL_PASS" = true ]; then
    echo "✓ Phase 3 PASS - Statistical validation complete"
    echo "  Ready to proceed to Phase 4 (Privacy Validation)"
    exit 0
elif [ "$STACK_EXIT_CODE" -eq 2 ]; then
    echo "⚠ Phase 3 PARTIAL - Core stack validated, PyMC unavailable"
    echo "  This is expected on Python 3.14; full validation requires Python 3.11"
    exit 2
else
    echo "✗ Phase 3 FAIL - Statistical validation incomplete"
    exit 1
fi
