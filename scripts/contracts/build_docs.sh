#!/bin/bash
# Documentation Build Script - Phase 4
# Generates immutable HTML docs from validated bundled artifacts with traceability

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Building Contract Documentation...${NC}"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST="$SCRIPT_DIR/entrypoints.json"
DIST_DIR="$ROOT_DIR/api-contracts/dist/openapi/v1"
DOCS_DIR="$ROOT_DIR/api-contracts/dist/docs/v1"

# Pre-flight checks
echo -e "${YELLOW}[1/4] Pre-flight checks...${NC}"

if [ ! -f "$MANIFEST" ]; then
    echo -e "${RED}ERROR: Manifest not found: $MANIFEST${NC}"
    exit 1
fi

if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}ERROR: Bundle directory not found: $DIST_DIR${NC}"
    echo -e "${YELLOW}Run: bash scripts/contracts/bundle.sh${NC}"
    exit 1
fi

# Check for Redocly CLI
if ! command -v redocly &> /dev/null; then
    echo -e "${YELLOW}  Redocly CLI not found, installing...${NC}"
    npm install -g @redocly/cli
    
    if ! command -v redocly &> /dev/null; then
        echo -e "${RED}ERROR: Failed to install Redocly CLI${NC}"
        exit 1
    fi
fi

REDOCLY_VERSION=$(redocly --version 2>&1 || echo "unknown")
echo -e "${GREEN}  ✓ Redocly CLI installed: $REDOCLY_VERSION${NC}"

# Create output directory
mkdir -p "$DOCS_DIR"
echo -e "${GREEN}  ✓ Output directory: $DOCS_DIR${NC}"

echo ""

# Get metadata
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "unknown")

echo -e "${YELLOW}[2/4] Building documentation for each domain...${NC}"

# Parse entrypoints and build docs
PYTHON_CMD=$(command -v python3 || command -v python)
BUILD_ERRORS=0
BUILT_COUNT=0

$PYTHON_CMD -c "
import json
with open('$MANIFEST') as f:
    for entry in json.load(f)['entrypoints']:
        print(f\"{entry['id']}|{entry['bundle']}\")
" | while IFS='|' read -r ENTRY_ID BUNDLE_PATH; do
    BUNDLE_FILE="$ROOT_DIR/$BUNDLE_PATH"
    DOC_FILE="$DOCS_DIR/${ENTRY_ID}.html"
    
    if [ ! -f "$BUNDLE_FILE" ]; then
        echo -e "${RED}  ✗ Bundle not found: $BUNDLE_FILE${NC}"
        BUILD_ERRORS=$((BUILD_ERRORS + 1))
        continue
    fi
    
    echo -e "  Building docs for ${ENTRY_ID}..."
    
    # Build documentation
    if redocly build-docs "$BUNDLE_FILE" --output="$DOC_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ ${ENTRY_ID}.html${NC}"
        BUILT_COUNT=$((BUILT_COUNT + 1))
    else
        echo -e "${RED}  ✗ Failed to build ${ENTRY_ID}${NC}"
        BUILD_ERRORS=$((BUILD_ERRORS + 1))
        continue
    fi
done

if [ $BUILD_ERRORS -gt 0 ]; then
    echo -e "${RED}✗ Build completed with $BUILD_ERRORS error(s)${NC}"
    exit 1
fi

echo ""

# Inject metadata into HTML files
echo -e "${YELLOW}[3/4] Injecting traceability metadata...${NC}"

for HTML_FILE in "$DOCS_DIR"/*.html; do
    if [ -f "$HTML_FILE" ]; then
        FILENAME=$(basename "$HTML_FILE")
        DOMAIN=$(basename "$FILENAME" .html)
        BUNDLE_REL="api-contracts/dist/openapi/v1/${DOMAIN}.bundled.yaml"
        
        # Create metadata tags
        META_VERSION="<meta name=\"contract-version\" content=\"$GIT_SHA\">"
        META_BUNDLE="<meta name=\"contract-bundle\" content=\"$BUNDLE_REL\">"
        META_TIMESTAMP="<meta name=\"build-timestamp\" content=\"$BUILD_TIMESTAMP\">"
        META_GENERATOR="<meta name=\"generator\" content=\"redocly-cli@$REDOCLY_VERSION\">"
        
        # Inject after <head> tag
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed
            sed -i '' "s|<head>|<head>\n  $META_VERSION\n  $META_BUNDLE\n  $META_TIMESTAMP\n  $META_GENERATOR|" "$HTML_FILE"
        else
            # Linux/Windows Git Bash sed
            sed -i "s|<head>|<head>\n  $META_VERSION\n  $META_BUNDLE\n  $META_TIMESTAMP\n  $META_GENERATOR|" "$HTML_FILE"
        fi
        
        echo -e "${GREEN}  ✓ Metadata injected: $FILENAME${NC}"
    fi
done

echo ""

# Create index page
echo -e "${YELLOW}[4/4] Creating index page...${NC}"

INDEX_FILE="$DOCS_DIR/index.html"

cat > "$INDEX_FILE" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skeldir 2.0 API Documentation</title>
    <meta name="contract-version" content="GIT_SHA_PLACEHOLDER">
    <meta name="build-timestamp" content="BUILD_TIMESTAMP_PLACEHOLDER">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 2.5rem;
        }
        .subtitle {
            color: #718096;
            margin-bottom: 30px;
            font-size: 1.1rem;
        }
        .metadata {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            color: #4a5568;
        }
        .metadata div { margin: 5px 0; }
        .metadata strong { color: #2d3748; }
        h2 {
            color: #2d3748;
            margin: 30px 0 20px 0;
            font-size: 1.5rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        .api-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .api-card {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            text-decoration: none;
            color: #2d3748;
            transition: all 0.2s;
            display: block;
        }
        .api-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .api-card h3 {
            font-size: 1.1rem;
            margin-bottom: 8px;
            color: #667eea;
        }
        .api-card p {
            font-size: 0.9rem;
            color: #718096;
        }
        .footer {
            text-align: center;
            color: #a0aec0;
            font-size: 0.85rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Skeldir 2.0 API Documentation</h1>
        <p class="subtitle">Contract-First Attribution Intelligence Platform</p>
        
        <div class="metadata">
            <div><strong>Contract Version:</strong> GIT_SHA_PLACEHOLDER</div>
            <div><strong>Build Timestamp:</strong> BUILD_TIMESTAMP_PLACEHOLDER</div>
            <div><strong>Source:</strong> Validated bundled artifacts (api-contracts/dist/openapi/v1/)</div>
        </div>
        
        <h2>Core APIs</h2>
        <div class="api-grid">
            <a href="auth.html" class="api-card">
                <h3>Authentication API</h3>
                <p>Login, token management, session control</p>
            </a>
            <a href="attribution.html" class="api-card">
                <h3>Attribution API</h3>
                <p>Revenue attribution, realtime metrics, analytics</p>
            </a>
            <a href="reconciliation.html" class="api-card">
                <h3>Reconciliation API</h3>
                <p>Data reconciliation, discrepancy resolution</p>
            </a>
            <a href="export.html" class="api-card">
                <h3>Export API</h3>
                <p>Data export, report generation</p>
            </a>
            <a href="health.html" class="api-card">
                <h3>Health API</h3>
                <p>Service health checks, monitoring</p>
            </a>
        </div>
        
        <h2>Webhook APIs</h2>
        <div class="api-grid">
            <a href="webhooks_shopify.html" class="api-card">
                <h3>Shopify Webhooks</h3>
                <p>Shopify integration events</p>
            </a>
            <a href="webhooks_woocommerce.html" class="api-card">
                <h3>WooCommerce Webhooks</h3>
                <p>WooCommerce integration events</p>
            </a>
            <a href="webhooks_stripe.html" class="api-card">
                <h3>Stripe Webhooks</h3>
                <p>Stripe payment events</p>
            </a>
            <a href="webhooks_paypal.html" class="api-card">
                <h3>PayPal Webhooks</h3>
                <p>PayPal payment events</p>
            </a>
        </div>
        
        <div class="footer">
            Generated from validated contract bundles | Contract-First Development | Skeldir 2.0
        </div>
    </div>
</body>
</html>
EOF

# Replace placeholders
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|GIT_SHA_PLACEHOLDER|$GIT_SHA|g" "$INDEX_FILE"
    sed -i '' "s|BUILD_TIMESTAMP_PLACEHOLDER|$BUILD_TIMESTAMP|g" "$INDEX_FILE"
else
    sed -i "s|GIT_SHA_PLACEHOLDER|$GIT_SHA|g" "$INDEX_FILE"
    sed -i "s|BUILD_TIMESTAMP_PLACEHOLDER|$BUILD_TIMESTAMP|g" "$INDEX_FILE"
fi

echo -e "${GREEN}  ✓ Index page created${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Documentation Build Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Built:${NC} 9 domain docs + 1 index page"
echo -e "${GREEN}Location:${NC} $DOCS_DIR"
echo -e "${GREEN}Metadata:${NC}"
echo "  - Contract Version: $GIT_SHA"
echo "  - Build Timestamp: $BUILD_TIMESTAMP"
echo "  - Generator: $REDOCLY_VERSION"
echo ""
echo -e "${YELLOW}View documentation:${NC}"
echo "  Open: $DOCS_DIR/index.html"
echo ""



