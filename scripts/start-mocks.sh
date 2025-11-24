#!/bin/bash
# Replit-Native Mock Server Startup Script
# Binds Prism to validated bundled artifacts (api-contracts/dist/openapi/v1/*.bundled.yaml)
# Implements 3-mock limit for Replit port constraints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting SKELDIR 2.0 Mock Servers (Replit-Native)...${NC}"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT_DIR/api-contracts/dist/openapi/v1"
REGISTRY_FILE="$SCRIPT_DIR/contracts/mock_registry.json"
PID_FILE="$ROOT_DIR/.mocks.pid"

# Pre-flight checks
echo -e "${YELLOW}[1/4] Pre-flight checks...${NC}"

# Check if bundles exist
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}ERROR: Bundle directory not found: $DIST_DIR${NC}"
    echo -e "${YELLOW}Run: bash scripts/contracts/bundle.sh${NC}"
    exit 1
fi

# Count bundles
BUNDLE_COUNT=$(find "$DIST_DIR" -name "*.bundled.yaml" -type f | wc -l)
if [ "$BUNDLE_COUNT" -ne 9 ]; then
    echo -e "${RED}ERROR: Expected 9 bundles, found $BUNDLE_COUNT${NC}"
    echo -e "${YELLOW}Run: bash scripts/contracts/bundle.sh${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Found $BUNDLE_COUNT bundled contracts${NC}"

# Check if Prism is installed
if ! command -v prism &> /dev/null; then
    echo -e "${YELLOW}  Prism not found, installing globally...${NC}"
    npm install -g @stoplight/prism-cli
    
    if ! command -v prism &> /dev/null; then
        echo -e "${RED}ERROR: Failed to install Prism CLI${NC}"
        echo -e "${YELLOW}Run: npm install -g @stoplight/prism-cli${NC}"
        exit 1
    fi
fi

PRISM_VERSION=$(prism --version 2>&1 | head -n 1 || echo "unknown")
echo -e "${GREEN}  ✓ Prism CLI installed: $PRISM_VERSION${NC}"

# Check if mocks are already running
if [ -f "$PID_FILE" ]; then
    echo -e "${YELLOW}  Mocks already running (PID file exists)${NC}"
    echo -e "${YELLOW}  Run: bash scripts/stop-mocks.sh first${NC}"
    exit 1
fi

echo ""

# Parse registry for primary mocks
echo -e "${YELLOW}[2/4] Loading mock configuration...${NC}"

if [ ! -f "$REGISTRY_FILE" ]; then
    echo -e "${RED}ERROR: Mock registry not found: $REGISTRY_FILE${NC}"
    exit 1
fi

# Extract primary mocks using Python (cross-platform)
PYTHON_CMD=$(command -v python3 || command -v python)
PRIMARY_MOCKS=$($PYTHON_CMD -c "
import json
with open('$REGISTRY_FILE') as f:
    registry = json.load(f)
    for mock in registry['primary_mocks']:
        port = registry['port_mapping'][mock]
        print(f'{mock}:{port}')
" 2>/dev/null)

if [ -z "$PRIMARY_MOCKS" ]; then
    echo -e "${RED}ERROR: Failed to parse mock registry${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Primary mocks: auth, attribution, health${NC}"
echo -e "${GREEN}  ✓ Ports: 4010, 4011, 4012${NC}"
echo ""

# Start mock servers
echo -e "${YELLOW}[3/4] Starting mock servers as background processes...${NC}"

# Clear PID file
> "$PID_FILE"

# Start each primary mock
while IFS=: read -r MOCK_ID PORT; do
    BUNDLE_FILE="$DIST_DIR/${MOCK_ID}.bundled.yaml"
    
    if [ ! -f "$BUNDLE_FILE" ]; then
        echo -e "${RED}  ✗ Bundle not found: $BUNDLE_FILE${NC}"
        continue
    fi
    
    echo -e "  Starting ${MOCK_ID} on port ${PORT}..."
    
    # Start Prism in background
    prism mock "$BUNDLE_FILE" -p "$PORT" -h 0.0.0.0 > "/tmp/prism-${MOCK_ID}.log" 2>&1 &
    PID=$!
    
    # Save PID
    echo "${MOCK_ID}:${PID}" >> "$PID_FILE"
    
    # Give it a moment to start
    sleep 1
    
    # Check if process is still running
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ ${MOCK_ID} started (PID: $PID)${NC}"
    else
        echo -e "${RED}  ✗ ${MOCK_ID} failed to start${NC}"
        cat "/tmp/prism-${MOCK_ID}.log"
    fi
done <<< "$PRIMARY_MOCKS"

echo ""

# Health checks
echo -e "${YELLOW}[4/4] Verifying mock server health...${NC}"
sleep 3  # Give servers time to fully initialize

# Check auth
echo -e "  Checking auth mock (port 4010)..."
AUTH_CHECK=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: health-check" \
    -d '{"email":"test@example.com","password":"test"}' \
    -w "\n%{http_code}" 2>/dev/null | tail -1 || echo "000")

if [ "$AUTH_CHECK" = "200" ] || [ "$AUTH_CHECK" = "401" ]; then
    echo -e "${GREEN}  ✓ Auth mock responding (HTTP $AUTH_CHECK)${NC}"
else
    echo -e "${RED}  ✗ Auth mock not responding (HTTP $AUTH_CHECK)${NC}"
fi

# Check attribution
echo -e "  Checking attribution mock (port 4011)..."
ATTR_CHECK=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: health-check" \
    -w "\n%{http_code}" 2>/dev/null | tail -1 || echo "000")

if [ "$ATTR_CHECK" = "200" ]; then
    echo -e "${GREEN}  ✓ Attribution mock responding (HTTP $ATTR_CHECK)${NC}"
else
    echo -e "${RED}  ✗ Attribution mock not responding (HTTP $ATTR_CHECK)${NC}"
fi

# Check health
echo -e "  Checking health mock (port 4012)..."
HEALTH_CHECK=$(curl -s http://localhost:4012/api/health \
    -w "\n%{http_code}" 2>/dev/null | tail -1 || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}  ✓ Health mock responding (HTTP $HEALTH_CHECK)${NC}"
else
    echo -e "${RED}  ✗ Health mock not responding (HTTP $HEALTH_CHECK)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Mock Servers Operational${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  Auth:          http://localhost:4010"
echo "  Attribution:   http://localhost:4011"
echo "  Health:        http://localhost:4012"
echo ""
echo -e "${YELLOW}On-Demand Mocks (use switch-mock.sh):${NC}"
echo "  - reconciliation"
echo "  - export"
echo "  - webhooks.shopify"
echo "  - webhooks.woocommerce"
echo "  - webhooks.stripe"
echo "  - webhooks.paypal"
echo ""
echo -e "${GREEN}All 3 primary mocks are running${NC}"
echo -e "${YELLOW}PIDs stored in: .mocks.pid${NC}"
echo ""
echo -e "To stop mocks: ${YELLOW}bash scripts/stop-mocks.sh${NC}"
echo -e "To switch on-demand mock: ${YELLOW}bash scripts/switch-mock.sh <domain>${NC}"
echo ""
