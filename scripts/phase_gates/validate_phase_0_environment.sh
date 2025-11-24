#!/bin/bash
# Phase 0 - Environment Precondition Validation
# Purpose: Verify Replit environment meets all prerequisites for empirical validation
# Exit Code: 0 if all checks pass, 1 if any check fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/evidence_registry/runtime"

echo "======================================================================="
echo "Phase 0 - Environment Precondition Validation"
echo "Timestamp: $(date -Iseconds)"
echo "Environment: Replit with Python 3.11"
echo "======================================================================="

# Initialize status tracking
ALL_PASS=true

# Create evidence directory
echo ""
echo "[1/6] Creating evidence_registry/runtime/ directory..."
mkdir -p "$EVIDENCE_DIR"
if [ -d "$EVIDENCE_DIR" ]; then
    echo "✓ PASS: evidence_registry/runtime/ created successfully"
else
    echo "✗ FAIL: Could not create evidence_registry/runtime/"
    ALL_PASS=false
fi

# Check Python availability and version
echo ""
echo "[2/6] Verifying Python availability..."
if command -v python > /dev/null 2>&1; then
    python --version > "$EVIDENCE_DIR/python_version.txt" 2>&1
    which python >> "$EVIDENCE_DIR/python_version.txt" 2>&1
    PYTHON_VERSION=$(python --version 2>&1)
    echo "✓ PASS: Python available - $PYTHON_VERSION"
    echo "  Evidence: evidence_registry/runtime/python_version.txt"
else
    echo "✗ FAIL: Python not found in PATH"
    echo "Python not found" > "$EVIDENCE_DIR/python_version.txt"
    ALL_PASS=false
fi

# Check Node availability and version
echo ""
echo "[3/6] Verifying Node.js availability..."
if command -v node > /dev/null 2>&1; then
    node --version > "$EVIDENCE_DIR/node_version.txt" 2>&1
    npm --version >> "$EVIDENCE_DIR/node_version.txt" 2>&1
    NODE_VERSION=$(node --version 2>&1)
    NPM_VERSION=$(npm --version 2>&1)
    echo "✓ PASS: Node.js available - $NODE_VERSION"
    echo "✓ PASS: npm available - $NPM_VERSION"
    echo "  Evidence: evidence_registry/runtime/node_version.txt"
else
    echo "✗ FAIL: Node.js not found in PATH"
    echo "Node.js not found" > "$EVIDENCE_DIR/node_version.txt"
    ALL_PASS=false
fi

# Check Procfile runner (foreman or overmind)
echo ""
echo "[4/6] Verifying Procfile runner availability..."
PROCFILE_RUNNER=""
if command -v foreman > /dev/null 2>&1; then
    PROCFILE_RUNNER="foreman"
    foreman version > "$EVIDENCE_DIR/procfile_runner.txt" 2>&1 || echo "foreman available" > "$EVIDENCE_DIR/procfile_runner.txt"
    echo "✓ PASS: foreman available"
elif command -v overmind > /dev/null 2>&1; then
    PROCFILE_RUNNER="overmind"
    overmind version > "$EVIDENCE_DIR/procfile_runner.txt" 2>&1 || echo "overmind available" > "$EVIDENCE_DIR/procfile_runner.txt"
    echo "✓ PASS: overmind available"
else
    echo "⚠ WARN: No Procfile runner found (foreman/overmind)"
    echo "  Note: Can start services manually in Replit"
    echo "No Procfile runner found" > "$EVIDENCE_DIR/procfile_runner.txt"
    # Not failing for this - Replit can run without explicit runner
fi

# Test file creation capability
echo ""
echo "[5/6] Testing evidence_registry/ write capability..."
TEST_FILE="$EVIDENCE_DIR/write_test_$(date +%s).txt"
if echo "Test write at $(date -Iseconds)" > "$TEST_FILE" 2>/dev/null; then
    echo "✓ PASS: Can write to evidence_registry/runtime/"
    rm -f "$TEST_FILE"
else
    echo "✗ FAIL: Cannot write to evidence_registry/runtime/"
    ALL_PASS=false
fi

# Verify critical binaries for later phases
echo ""
echo "[6/6] Verifying critical binaries for downstream phases..."
BINARIES_STATUS="$EVIDENCE_DIR/binary_availability.txt"
{
    echo "=== Binary Availability Check ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    # curl for API testing
    if command -v curl > /dev/null 2>&1; then
        echo "✓ curl: $(curl --version | head -1)"
    else
        echo "✗ curl: NOT FOUND"
    fi
    
    # psql for database testing
    if command -v psql > /dev/null 2>&1; then
        echo "✓ psql: $(psql --version)"
    else
        echo "✗ psql: NOT FOUND (required for Phase 4)"
    fi
    
    # lsof for port checking
    if command -v lsof > /dev/null 2>&1; then
        echo "✓ lsof: available"
    else
        echo "⚠ lsof: NOT FOUND (may use netstat as fallback)"
    fi
    
    # prism for mock servers
    if command -v prism > /dev/null 2>&1; then
        echo "✓ prism: $(prism --version 2>&1 || echo 'available')"
    else
        echo "⚠ prism: NOT FOUND (optional for contract mocks)"
    fi
    
} > "$BINARIES_STATUS"

cat "$BINARIES_STATUS"

# Generate summary
echo ""
echo "======================================================================="
echo "Phase 0 Exit Criteria Summary"
echo "======================================================================="

{
    echo "=== Phase 0 Precondition Status ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    echo "Exit Criteria:"
    echo "  1. Python executable found: $(command -v python > /dev/null 2>&1 && echo PASS || echo FAIL)"
    echo "  2. Node/npm executable found: $(command -v node > /dev/null 2>&1 && echo PASS || echo FAIL)"
    echo "  3. Procfile runner available: ${PROCFILE_RUNNER:-N/A (manual start)}"
    echo "  4. evidence_registry/ writable: $([ -w "$EVIDENCE_DIR" ] && echo PASS || echo FAIL)"
    echo ""
    echo "Overall Status: $([ "$ALL_PASS" = true ] && echo PASS || echo FAIL)"
    echo ""
    echo "Evidence Files Created:"
    echo "  - python_version.txt"
    echo "  - node_version.txt"
    echo "  - procfile_runner.txt"
    echo "  - binary_availability.txt"
    echo "  - phase_0_precondition_status.txt"
    
} | tee "$EVIDENCE_DIR/phase_0_precondition_status.txt"

echo ""
echo "======================================================================="

if [ "$ALL_PASS" = true ]; then
    echo "✓ Phase 0 PASS - All preconditions met"
    echo "  Ready to proceed to Phase 1 (Runtime Validation)"
    exit 0
else
    echo "✗ Phase 0 FAIL - Some preconditions not met"
    echo "  Fix environment issues before proceeding"
    exit 1
fi
