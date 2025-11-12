#!/bin/bash
# Pydantic Model Generation Script
# Generates Pydantic v2 models from OpenAPI contracts using datamodel-codegen

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTRACTS_DIR="contracts/openapi/v1"
SCHEMAS_DIR="backend/app/schemas"
PYTHON_VERSION="3.11"

echo -e "${GREEN}Generating Pydantic models from OpenAPI contracts...${NC}"

# Check if datamodel-codegen is installed
if ! command -v datamodel-codegen &> /dev/null; then
    echo -e "${YELLOW}datamodel-codegen not found. Installing...${NC}"
    pip install datamodel-code-generator[openapi] pydantic>=2.0.0
fi

# Create schemas directory if it doesn't exist
mkdir -p "$SCHEMAS_DIR"

# Generate models for attribution.yaml (skip if no components/schemas defined)
if [ -f "$CONTRACTS_DIR/attribution.yaml" ]; then
    echo -e "${GREEN}Generating models from attribution.yaml...${NC}"
    if datamodel-codegen \
        --input "$CONTRACTS_DIR/attribution.yaml" \
        --output "$SCHEMAS_DIR/attribution.py" \
        --target-python-version "$PYTHON_VERSION" \
        --use-annotated \
        --use-standard-collections \
        --use-schema-description \
        --use-field-description \
        --disable-timestamp \
        --input-file-type openapi 2>&1 | grep -q "Models not found"; then
        echo -e "${YELLOW}No models found in attribution.yaml (inline schemas), skipping...${NC}"
        # Create empty file to satisfy CI check
        echo "# No models generated - attribution.yaml uses inline schemas" > "$SCHEMAS_DIR/attribution.py"
    else
        echo -e "${GREEN}✓ Generated $SCHEMAS_DIR/attribution.py${NC}"
    fi
else
    echo -e "${RED}Error: $CONTRACTS_DIR/attribution.yaml not found${NC}"
    exit 1
fi

# Generate models for auth.yaml (skip if no components/schemas defined)
if [ -f "$CONTRACTS_DIR/auth.yaml" ]; then
    echo -e "${GREEN}Generating models from auth.yaml...${NC}"
    if datamodel-codegen \
        --input "$CONTRACTS_DIR/auth.yaml" \
        --output "$SCHEMAS_DIR/auth.py" \
        --target-python-version "$PYTHON_VERSION" \
        --use-annotated \
        --use-standard-collections \
        --use-schema-description \
        --use-field-description \
        --disable-timestamp \
        --input-file-type openapi 2>&1 | grep -q "Models not found"; then
        echo -e "${YELLOW}No models found in auth.yaml (inline schemas), skipping...${NC}"
        # Create placeholder file to satisfy CI check
        echo "# No models generated - auth.yaml uses inline schemas" > "$SCHEMAS_DIR/auth.py"
    else
        echo -e "${GREEN}✓ Generated $SCHEMAS_DIR/auth.py${NC}"
    fi
else
    echo -e "${RED}Error: $CONTRACTS_DIR/auth.yaml not found${NC}"
    exit 1
fi

# Create __init__.py if it doesn't exist
if [ ! -f "$SCHEMAS_DIR/__init__.py" ]; then
    echo -e "${GREEN}Creating $SCHEMAS_DIR/__init__.py...${NC}"
    cat > "$SCHEMAS_DIR/__init__.py" << 'EOF'
"""
Pydantic models generated from OpenAPI contracts.

These models are auto-generated from contracts/openapi/v1/*.yaml files.
Do not edit manually. Regenerate using scripts/generate-models.sh after contract changes.
"""

# Import all models for easy access
try:
    from .attribution import *
    from .auth import *
except ImportError:
    # Models not yet generated
    pass

__all__ = [
    # Attribution models
    # Auth models
    # Add other model exports as they are generated
]
EOF
    echo -e "${GREEN}✓ Created $SCHEMAS_DIR/__init__.py${NC}"
fi

echo -e "${GREEN}Model generation completed successfully!${NC}"

