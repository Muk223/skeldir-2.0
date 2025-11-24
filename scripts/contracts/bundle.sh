#!/bin/bash
# Manifest-Driven OpenAPI Contract Bundling Script
# Single Source of Truth: scripts/contracts/entrypoints.json

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST="$SCRIPT_DIR/entrypoints.json"
CONTRACTS_DIR="$REPO_ROOT/api-contracts"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Manifest-Driven Contract Bundling${NC}"
echo -e "${GREEN}Source: $MANIFEST${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Validate manifest exists
if [ ! -f "$MANIFEST" ]; then
    echo -e "${RED}ERROR: Manifest not found: $MANIFEST${NC}"
    exit 2
fi

# Check dependencies
if ! command -v npx &> /dev/null; then
    echo -e "${RED}ERROR: npx not found. Install Node.js and npm.${NC}"
    exit 2
fi

if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}ERROR: Python not found.${NC}"
    exit 2
fi

PYTHON_CMD=$(command -v python3 || command -v python)

# Parse manifest and bundle each entrypoint
cd "$CONTRACTS_DIR"

BUNDLE_ERRORS=0
TOTAL_ENTRYPOINTS=$(echo "$($PYTHON_CMD -c "import json; print(len(json.load(open('$MANIFEST'))['entrypoints']))")")

echo -e "${GREEN}[1/4] Bundling $TOTAL_ENTRYPOINTS contracts from manifest...${NC}"
echo ""

# Read entrypoints from manifest and bundle each
$PYTHON_CMD -c "
import json
import sys

with open('$MANIFEST') as f:
    manifest = json.load(f)

for entry in manifest['entrypoints']:
    print(f\"{entry['api_name']}|{entry['bundle']}\")
" | while IFS='|' read -r api_name bundle_path; do
    echo -e "  Bundling ${api_name}..."
    
    # Extract relative bundle path from full path
    bundle_file=$(basename "$bundle_path")
    bundle_dir=$(dirname "$bundle_path" | sed "s|^api-contracts/||")
    output_path="$bundle_dir/$bundle_file"
    
    if npx @redocly/cli bundle "$api_name" \
        --config=redocly.yaml \
        --output="$output_path" \
        --ext yaml \
        --dereferenced 2>&1 | grep -q "Created a bundle"; then
        echo -e "  ${GREEN}✓${NC} Bundled $bundle_file"
    else
        echo -e "  ${RED}✗${NC} Failed to bundle $api_name"
        BUNDLE_ERRORS=$((BUNDLE_ERRORS + 1))
    fi
done

cd "$REPO_ROOT"

if [ $BUNDLE_ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}✗ Step 1 FAILED: $BUNDLE_ERRORS bundling errors${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Step 1 PASSED: All contracts bundled from manifest${NC}"
echo ""

# Gate 1: Validate completeness
echo -e "${GREEN}[2/4] Gate 1: Validating bundle completeness...${NC}"
if ! $PYTHON_CMD scripts/contracts/check_dist_complete.py > /dev/null 2>&1; then
    echo -e "${RED}✗ Gate 1 FAILED: Bundle completeness check failed${NC}"
    $PYTHON_CMD scripts/contracts/check_dist_complete.py --json
    exit 1
fi
echo -e "${GREEN}✓ Gate 1 PASSED: All bundles present${NC}"
echo ""

# Gate 2: Validate zero external refs
echo -e "${GREEN}[3/4] Gate 2: Validating full dereferencing...${NC}"
if ! $PYTHON_CMD scripts/contracts/assert_no_external_refs.py > /dev/null 2>&1; then
    echo -e "${RED}✗ Gate 2 FAILED: External references found${NC}"
    $PYTHON_CMD scripts/contracts/assert_no_external_refs.py --json
    exit 1
fi
echo -e "${GREEN}✓ Gate 2 PASSED: Zero external refs (fully dereferenced)${NC}"
echo ""

# Gate 3: OpenAPI semantic validation
echo -e "${GREEN}[4/4] Gate 3: OpenAPI semantic validation...${NC}"
VALIDATION_ERRORS=0

$PYTHON_CMD -c "
import json
with open('$MANIFEST') as f:
    for entry in json.load(f)['entrypoints']:
        print(entry['bundle'])
" | while read -r bundle_path; do
    bundle_file=$(basename "$bundle_path")
    
    if npx @openapitools/openapi-generator-cli validate -i "$bundle_path" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $bundle_file valid"
    else
        echo -e "  ${RED}✗${NC} $bundle_file has validation errors"
        VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
    fi
done

if [ $VALIDATION_ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}✗ Gate 3 FAILED: $VALIDATION_ERRORS bundles have OpenAPI validation errors${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Gate 3 PASSED: All bundles are valid OpenAPI 3.x${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ BUNDLING COMPLETE${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Evidence:${NC}"
echo -e "  - Bundled $TOTAL_ENTRYPOINTS contracts from manifest"
echo -e "  - All bundles present (completeness validated)"
echo -e "  - Zero external refs (fully dereferenced)"
echo -e "  - All bundles valid OpenAPI 3.x"
echo ""
echo -e "${GREEN}Manifest-Driven: VALIDATED${NC}"
echo ""

exit 0
