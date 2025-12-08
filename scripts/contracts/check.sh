#!/bin/bash
# Unified Contract Validation Script
# Performs bundling, validation, and optional model generation smoke test

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUNDLE_SCRIPT="$SCRIPT_DIR/bundle.sh"
DIST_DIR="$ROOT_DIR/api-contracts/dist/openapi/v1"

# Parse arguments
RUN_MODEL_TEST=${1:-false}
FOCUSED_DOMAIN=${2:-""}

echo -e "${GREEN}Running contract validation pipeline...${NC}"
echo ""

# Step 1: Bundle all contracts
echo -e "${GREEN}[1/3] Bundling contracts...${NC}"
cd "$ROOT_DIR"
if ! bash "$BUNDLE_SCRIPT"; then
    echo -e "${RED}✗ Bundling failed${NC}"
    exit 1
fi
echo ""

# Step 2: Validate bundled files
echo -e "${GREEN}[2/3] Validating bundled OpenAPI files...${NC}"
VALIDATION_ERRORS=0

if [ -n "$FOCUSED_DOMAIN" ]; then
    # Validate only the focused domain
    BUNDLED_FILE="$DIST_DIR/${FOCUSED_DOMAIN}.bundled.yaml"
    if [ -f "$BUNDLED_FILE" ]; then
        echo "Validating $(basename $BUNDLED_FILE)..."
        if npx @openapitools/openapi-generator-cli validate -i "$BUNDLED_FILE" 2>&1; then
            echo -e "${GREEN}✓ $(basename $BUNDLED_FILE) is valid${NC}"
        else
            echo -e "${RED}✗ $(basename $BUNDLED_FILE) validation failed${NC}"
            VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
        fi
    else
        echo -e "${RED}✗ Bundled file not found: $BUNDLED_FILE${NC}"
        VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
    fi
else
    # Validate all bundled files
    for file in "$DIST_DIR"/*.bundled.yaml; do
        if [ -f "$file" ]; then
            echo "Validating $(basename $file)..."
            if npx @openapitools/openapi-generator-cli validate -i "$file" 2>&1; then
                echo -e "${GREEN}✓ $(basename $file) is valid${NC}"
            else
                echo -e "${RED}✗ $(basename $file) validation failed${NC}"
                VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
            fi
        fi
    done
fi

if [ $VALIDATION_ERRORS -gt 0 ]; then
    echo -e "${RED}✗ Validation completed with $VALIDATION_ERRORS error(s)${NC}"
    exit 1
fi
echo ""

# Step 3: Optional model generation smoke test
if [ "$RUN_MODEL_TEST" = "true" ] || [ "$RUN_MODEL_TEST" = "smoke" ]; then
    echo -e "${GREEN}[3/3] Running model generation smoke test...${NC}"
    
    # Test on auth and attribution bundles
    TEST_DOMAINS=("auth" "attribution")
    SMOKE_ERRORS=0
    
    for domain in "${TEST_DOMAINS[@]}"; do
        BUNDLED_FILE="$DIST_DIR/${domain}.bundled.yaml"
        if [ -f "$BUNDLED_FILE" ]; then
            echo "Testing model generation for ${domain}..."
            TEMP_DIR=$(mktemp -d)
            
            if python -m datamodel_code_generator \
                --input "$BUNDLED_FILE" \
                --input-file-type openapi \
                --output "$TEMP_DIR" \
                --target-python-version 3.11 \
                --use-annotated \
                --use-standard-collections 2>&1; then
                
                # Check if any .py files were generated
                PY_COUNT=$(find "$TEMP_DIR" -name "*.py" -type f | wc -l)
                if [ "$PY_COUNT" -gt 0 ]; then
                    echo -e "${GREEN}✓ Generated $PY_COUNT Python file(s) for ${domain}${NC}"
                else
                    echo -e "${YELLOW}⚠ No Python files generated for ${domain} (may be expected)${NC}"
                fi
                
                # For attribution, check for RealtimeRevenueResponse
                if [ "$domain" = "attribution" ]; then
                    if grep -r "RealtimeRevenueResponse" "$TEMP_DIR" 2>/dev/null; then
                        echo -e "${GREEN}✓ RealtimeRevenueResponse found in generated models${NC}"
                    else
                        echo -e "${YELLOW}⚠ RealtimeRevenueResponse not found (may need schema extraction)${NC}"
                    fi
                fi
            else
                echo -e "${RED}✗ Model generation failed for ${domain}${NC}"
                SMOKE_ERRORS=$((SMOKE_ERRORS + 1))
            fi
            
            rm -rf "$TEMP_DIR"
        fi
    done
    
    if [ $SMOKE_ERRORS -gt 0 ]; then
        echo -e "${RED}✗ Model generation smoke test completed with $SMOKE_ERRORS error(s)${NC}"
        exit 1
    fi
    echo ""
fi

# Summary
echo -e "${GREEN}✓ Contract validation pipeline completed successfully!${NC}"
echo ""
echo "Bundled artifacts: $DIST_DIR"
echo "To run with model generation smoke test: $0 smoke"
echo "To validate a specific domain: $0 false <domain>"





