#!/bin/bash
# Run All Empirical Validation Phases
# Purpose: Execute all phase validation scripts in sequence
# Exit Code: 0 if all phases pass, >0 if any phase fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "======================================================================="
echo "Empirical Validation Framework - Full Execution"
echo "Timestamp: $(date -Iseconds)"
echo "Running Phases 0-5"
echo "======================================================================="

FAILED_PHASES=()

# Phase 0
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 0: Environment Preconditions"
echo "═══════════════════════════════════════════════════════════════════════"
if bash "$SCRIPT_DIR/validate_phase_0_environment.sh"; then
    echo "✓ Phase 0 PASS"
else
    echo "✗ Phase 0 FAIL"
    FAILED_PHASES+=("Phase 0")
fi

# Phase 1
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 1: Runtime Validation"
echo "═══════════════════════════════════════════════════════════════════════"
if bash "$SCRIPT_DIR/validate_phase_1_runtime.sh"; then
    echo "✓ Phase 1 PASS"
else
    echo "✗ Phase 1 FAIL"
    FAILED_PHASES+=("Phase 1")
fi

# Phase 2
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 2: Contract Validation"
echo "═══════════════════════════════════════════════════════════════════════"
if bash "$SCRIPT_DIR/validate_phase_2_contracts.sh"; then
    echo "✓ Phase 2 PASS"
else
    echo "✗ Phase 2 FAIL"
    FAILED_PHASES+=("Phase 2")
fi

# Phase 3
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 3: Statistical Validation"
echo "═══════════════════════════════════════════════════════════════════════"
PHASE3_EXIT_CODE=0
bash "$SCRIPT_DIR/validate_phase_3_statistics.sh" || PHASE3_EXIT_CODE=$?
if [ $PHASE3_EXIT_CODE -eq 0 ]; then
    echo "✓ Phase 3 PASS (Full Success)"
elif [ $PHASE3_EXIT_CODE -eq 2 ]; then
    echo "⚠ Phase 3 PARTIAL (Core stack validated, PyMC unavailable)"
    # Not adding to FAILED_PHASES - partial is acceptable
else
    echo "✗ Phase 3 FAIL"
    FAILED_PHASES+=("Phase 3")
fi

# Phase 4
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 4: Privacy Validation"
echo "═══════════════════════════════════════════════════════════════════════"
if bash "$SCRIPT_DIR/validate_phase_4_privacy.sh"; then
    echo "✓ Phase 4 PASS"
else
    echo "✗ Phase 4 FAIL"
    FAILED_PHASES+=("Phase 4")
fi

# Phase 5
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 5: Manifest Generation"
echo "═══════════════════════════════════════════════════════════════════════"
if bash "$SCRIPT_DIR/validate_phase_5_manifest.sh"; then
    echo "✓ Phase 5 PASS"
else
    echo "✗ Phase 5 FAIL"
    FAILED_PHASES+=("Phase 5")
fi

# Final Summary
echo ""
echo "======================================================================="
echo "EMPIRICAL VALIDATION SUMMARY"
echo "======================================================================="
echo ""

if [ ${#FAILED_PHASES[@]} -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║     ✓ ALL PHASES PASSED - EMPIRICAL VALIDATION COMPLETE         ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Evidence Chain: evidence_registry/EMPIRICAL_CHAIN.md"
    echo "Ready to proceed to Phase 5.2 (CI Integration)"
    exit 0
else
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║     ✗ SOME PHASES FAILED - REVIEW REQUIRED                      ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Failed Phases:"
    for phase in "${FAILED_PHASES[@]}"; do
        echo "  - $phase"
    done
    echo ""
    echo "Review evidence files in evidence_registry/ to diagnose issues"
    exit 1
fi
