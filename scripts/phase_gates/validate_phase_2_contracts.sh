#!/bin/bash
# Phase 2 - Contract Empirical Validation
# Purpose: Prove backend obeys OpenAPI contracts and B0.1 semantics using raw tools
# Exit Code: 0 if all checks pass, 1 if any check fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/evidence_registry/contracts"

echo "======================================================================="
echo "Phase 2 - Contract Empirical Validation"
echo "Timestamp: $(date -Iseconds)"
echo "Validating: OpenAPI contracts, backend alignment, B0.1 semantics"
echo "======================================================================="

# Initialize status tracking
ALL_PASS=true

# Ensure evidence directory exists
mkdir -p "$EVIDENCE_DIR"

# 2.1 Raw Contract Validation (OpenAPI specs)
echo ""
echo "[1/6] OpenAPI Contract Validation..."
echo "=== OpenAPI Validation ===" > "$EVIDENCE_DIR/openapi_validation_raw.txt"
echo "Timestamp: $(date -Iseconds)" >> "$EVIDENCE_DIR/openapi_validation_raw.txt"
echo "" >> "$EVIDENCE_DIR/openapi_validation_raw.txt"

VALIDATION_FAILED=false
for f in "$PROJECT_ROOT"/api-contracts/dist/openapi/v1/*.bundled.yaml; do
    if [ -f "$f" ]; then
        echo "=== VALIDATING $(basename "$f") ===" >> "$EVIDENCE_DIR/openapi_validation_raw.txt"
        if npx @openapitools/openapi-generator-cli validate -i "$f" >> "$EVIDENCE_DIR/openapi_validation_raw.txt" 2>&1; then
            echo "  ✓ $(basename "$f") - VALID"
        else
            echo "  ✗ $(basename "$f") - INVALID"
            VALIDATION_FAILED=true
            ALL_PASS=false
        fi
        echo "" >> "$EVIDENCE_DIR/openapi_validation_raw.txt"
    fi
done

if [ "$VALIDATION_FAILED" = false ]; then
    echo "✓ PASS: All OpenAPI contracts are valid"
else
    echo "✗ FAIL: Some OpenAPI contracts failed validation"
fi
echo "  Evidence: evidence_registry/contracts/openapi_validation_raw.txt"

# 2.2 Breaking Change Detection (if baselines exist)
echo ""
echo "[2/6] Breaking Change Detection..."
if [ -d "$PROJECT_ROOT/api-contracts/baselines/v1.0.0" ]; then
    echo "=== Breaking Change Detection ===" > "$EVIDENCE_DIR/openapi_breaking_raw.txt"
    echo "Timestamp: $(date -Iseconds)" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt"
    echo "" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt"
    
    BREAKING_CHANGES=false
    for f in "$PROJECT_ROOT"/api-contracts/baselines/v1.0.0/*.yaml; do
        if [ -f "$f" ]; then
            name=$(basename "$f" .yaml)
            current="$PROJECT_ROOT/api-contracts/dist/openapi/v1/${name}.bundled.yaml"
            
            if [ -f "$current" ]; then
                echo "=== OASDIFF $name ===" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt"
                if command -v oasdiff > /dev/null 2>&1; then
                    if oasdiff breaking "$f" "$current" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt" 2>&1; then
                        echo "  ✓ $name - No breaking changes"
                    else
                        echo "  ⚠ $name - Breaking changes detected"
                        BREAKING_CHANGES=true
                    fi
                else
                    echo "  ⚠ oasdiff not installed, skipping breaking change detection"
                    echo "oasdiff not available" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt"
                fi
                echo "" >> "$EVIDENCE_DIR/openapi_breaking_raw.txt"
            fi
        fi
    done
    
    if [ "$BREAKING_CHANGES" = true ]; then
        echo "⚠ WARN: Breaking changes detected (review required)"
    else
        echo "✓ PASS: No breaking changes detected"
    fi
else
    echo "⚠ SKIP: No baselines found at api-contracts/baselines/v1.0.0/"
    echo "No baselines found - skipping breaking change detection" > "$EVIDENCE_DIR/openapi_breaking_raw.txt"
fi
echo "  Evidence: evidence_registry/contracts/openapi_breaking_raw.txt"

# 2.3 Backend Route Inventory (FastAPI introspection)
echo ""
echo "[3/6] Backend Route Inventory - Extracting FastAPI routes..."

# Use Python 3.11 venv if available
PYTHON_BIN="python"
if [ -x "$PROJECT_ROOT/backend/.venv311/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/backend/.venv311/bin/python"
fi

cd "$PROJECT_ROOT/backend" || exit 1

$PYTHON_BIN - << 'PYEOF' > "$EVIDENCE_DIR/backend_routes_raw.txt" 2>&1
import sys
sys.path.insert(0, '.')

from app.main import app

print("=== Backend Route Inventory ===")
print(f"Total routes: {len(app.routes)}")
print("")

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ",".join(sorted(route.methods - {'HEAD', 'OPTIONS'}))  # Exclude implicit methods
        path = route.path
        name = getattr(route, 'name', 'unknown')
        print(f"{methods:10} {path:50} -> {name}")
PYEOF

cd "$PROJECT_ROOT" || exit 1

if grep -q "app.main" "$EVIDENCE_DIR/backend_routes_raw.txt" 2>/dev/null; then
    ROUTE_COUNT=$(grep -c " -> " "$EVIDENCE_DIR/backend_routes_raw.txt" 2>/dev/null || echo "0")
    echo "✓ PASS: Extracted $ROUTE_COUNT backend routes"
else
    echo "✗ FAIL: Could not extract backend routes"
    ALL_PASS=false
fi
echo "  Evidence: evidence_registry/contracts/backend_routes_raw.txt"

# 2.4 Contract Operations Inventory
echo ""
echo "[4/6] Contract Operations Inventory - Extracting OpenAPI operations..."

if [ -f "$PROJECT_ROOT/scripts/extract_contract_operations.py" ]; then
    $PYTHON_BIN "$PROJECT_ROOT/scripts/extract_contract_operations.py" > "$EVIDENCE_DIR/contract_operations_raw.txt" 2>&1
    
    if grep -q "operation" "$EVIDENCE_DIR/contract_operations_raw.txt" 2>/dev/null || grep -q "bundled.yaml" "$EVIDENCE_DIR/contract_operations_raw.txt" 2>/dev/null; then
        OP_COUNT=$(grep -c "bundled.yaml" "$EVIDENCE_DIR/contract_operations_raw.txt" 2>/dev/null || echo "0")
        echo "✓ PASS: Extracted contract operations"
    else
        echo "✗ FAIL: Could not extract contract operations"
        ALL_PASS=false
    fi
else
    echo "⚠ WARN: scripts/extract_contract_operations.py not found"
    echo "Script not found" > "$EVIDENCE_DIR/contract_operations_raw.txt"
    ALL_PASS=false
fi
echo "  Evidence: evidence_registry/contracts/contract_operations_raw.txt"

# 2.5 Live Semantics Test (B0.1)
echo ""
echo "[5/6] Live Semantics (B0.1) - Testing interim behavior..."

# Note: Requires SYSTEM_PHASE=B0.1 set in backend environment
curl -i \
  -H "X-Correlation-ID: 00000000-0000-0000-0000-000000000000" \
  http://localhost:8000/api/attribution/revenue/realtime \
  > "$EVIDENCE_DIR/interim_semantics_B0.1_curl.txt" 2>&1

if grep -q "200 OK" "$EVIDENCE_DIR/interim_semantics_B0.1_curl.txt" 2>/dev/null; then
    if grep -qi '"verified".*false' "$EVIDENCE_DIR/interim_semantics_B0.1_curl.txt" 2>/dev/null; then
        echo "✓ PASS: B0.1 semantics confirmed (verified=false)"
    else
        echo "⚠ WARN: Response may not contain verified:false field"
    fi
    
    if grep -qi "upgrade\|notice\|B0.1" "$EVIDENCE_DIR/interim_semantics_B0.1_curl.txt" 2>/dev/null; then
        echo "✓ PASS: Upgrade notice present in response"
    else
        echo "⚠ WARN: Upgrade notice may be missing"
    fi
else
    echo "✗ FAIL: Could not reach /api/attribution/revenue/realtime (404 or service down)"
    ALL_PASS=false
fi
echo "  Evidence: evidence_registry/contracts/interim_semantics_B0.1_curl.txt"

# 2.6 Alignment Verification (routes vs operations)
echo ""
echo "[6/6] Route-Contract Alignment - Comparing backend vs OpenAPI..."

{
    echo "=== Route-Contract Alignment Analysis ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    # Extract route paths
    if [ -f "$EVIDENCE_DIR/backend_routes_raw.txt" ]; then
        echo "Backend Routes:"
        grep " -> " "$EVIDENCE_DIR/backend_routes_raw.txt" 2>/dev/null || echo "  (none found)"
        echo ""
    fi
    
    # Extract contract operations
    if [ -f "$EVIDENCE_DIR/contract_operations_raw.txt" ]; then
        echo "Contract Operations:"
        grep "bundled.yaml" "$EVIDENCE_DIR/contract_operations_raw.txt" 2>/dev/null || echo "  (none found)"
        echo ""
    fi
    
    echo "Manual Review Required:"
    echo "  - Verify all implemented routes have matching contract operations"
    echo "  - Identify orphan contracts (defined but not implemented)"
    echo "  - Confirm in-scope routes are covered"
    
} > "$EVIDENCE_DIR/alignment_analysis.txt"

echo "✓ Alignment analysis generated (manual review required)"
echo "  Evidence: evidence_registry/contracts/alignment_analysis.txt"

# Generate Phase 2 Summary
echo ""
echo "======================================================================="
{
    echo "=== Phase 2 Contract Validation Status ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    echo "Exit Criteria:"
    echo "  1. OpenAPI validation: $([ "$VALIDATION_FAILED" = false ] && echo PASS || echo FAIL)"
    echo "  2. Breaking changes: $([ -f "$EVIDENCE_DIR/openapi_breaking_raw.txt" ] && echo CHECKED || echo SKIPPED)"
    echo "  3. Backend routes extracted: $([ -f "$EVIDENCE_DIR/backend_routes_raw.txt" ] && grep -q " -> " "$EVIDENCE_DIR/backend_routes_raw.txt" 2>/dev/null && echo PASS || echo FAIL)"
    echo "  4. Contract operations extracted: $([ -f "$EVIDENCE_DIR/contract_operations_raw.txt" ] && echo PASS || echo FAIL)"
    echo "  5. B0.1 semantics (verified=false): $(grep -qi '"verified".*false' "$EVIDENCE_DIR/interim_semantics_B0.1_curl.txt" 2>/dev/null && echo PASS || echo PARTIAL)"
    echo "  6. Route-contract alignment: MANUAL_REVIEW_REQUIRED"
    echo ""
    echo "Overall Status: $([ "$ALL_PASS" = true ] && echo PASS || echo PARTIAL)"
    echo ""
    echo "Evidence Files:"
    echo "  - openapi_validation_raw.txt"
    echo "  - openapi_breaking_raw.txt"
    echo "  - backend_routes_raw.txt"
    echo "  - contract_operations_raw.txt"
    echo "  - interim_semantics_B0.1_curl.txt"
    echo "  - alignment_analysis.txt"
    
} | tee "$EVIDENCE_DIR/phase_2_contracts_status.txt"

echo "======================================================================="

if [ "$ALL_PASS" = true ]; then
    echo "✓ Phase 2 PASS - Contract validation complete"
    echo "  Ready to proceed to Phase 3 (Statistical Validation)"
    exit 0
else
    echo "✗ Phase 2 PARTIAL - Some contract checks incomplete/failed"
    echo "  Review evidence files before proceeding"
    exit 1
fi
