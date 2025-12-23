#!/bin/bash
# Switch On-Demand Mock Server
# Stops current on-demand mock and starts requested domain

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Usage
if [ -z "$1" ]; then
    echo -e "${RED}ERROR: Domain argument required${NC}"
    echo ""
    echo "Usage: $0 <domain>"
    echo ""
    echo "Available on-demand domains:"
    echo "  - reconciliation"
    echo "  - export"
    echo "  - webhooks.shopify"
    echo "  - webhooks.woocommerce"
    echo "  - webhooks.stripe"
    echo "  - webhooks.paypal"
    echo ""
    exit 1
fi

DOMAIN=$1

echo -e "${YELLOW}Switching on-demand mock to: $DOMAIN${NC}"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT_DIR/api-contracts/dist/openapi/v1"
REGISTRY_FILE="$SCRIPT_DIR/contracts/mock_registry.json"
PID_FILE="$ROOT_DIR/.mocks.pid"
ON_DEMAND_PORT=4013
export PATH="$ROOT_DIR/node_modules/.bin:$PATH"

# Map domain to bundle file
case "$DOMAIN" in
    "reconciliation")
        BUNDLE_FILE="$DIST_DIR/reconciliation.bundled.yaml"
        ;;
    "export")
        BUNDLE_FILE="$DIST_DIR/export.bundled.yaml"
        ;;
    "webhooks.shopify"|"shopify")
        BUNDLE_FILE="$DIST_DIR/webhooks.shopify.bundled.yaml"
        DOMAIN="webhooks.shopify"
        ;;
    "webhooks.woocommerce"|"woocommerce")
        BUNDLE_FILE="$DIST_DIR/webhooks.woocommerce.bundled.yaml"
        DOMAIN="webhooks.woocommerce"
        ;;
    "webhooks.stripe"|"stripe")
        BUNDLE_FILE="$DIST_DIR/webhooks.stripe.bundled.yaml"
        DOMAIN="webhooks.stripe"
        ;;
    "webhooks.paypal"|"paypal")
        BUNDLE_FILE="$DIST_DIR/webhooks.paypal.bundled.yaml"
        DOMAIN="webhooks.paypal"
        ;;
    *)
        echo -e "${RED}ERROR: Unknown domain: $DOMAIN${NC}"
        echo -e "${YELLOW}Run: $0 (without args) for usage${NC}"
        exit 1
        ;;
esac

# Check if bundle exists
if [ ! -f "$BUNDLE_FILE" ]; then
    echo -e "${RED}ERROR: Bundle not found: $BUNDLE_FILE${NC}"
    echo -e "${YELLOW}Run: bash scripts/contracts/bundle.sh${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Bundle found: $(basename "$BUNDLE_FILE")${NC}"
echo ""

# Stop existing on-demand mock if running
echo -e "${YELLOW}[1/2] Stopping existing on-demand mock...${NC}"

if [ -f "$PID_FILE" ]; then
    # Find and kill on-demand process
    ON_DEMAND_PID=$(grep "^on-demand:" "$PID_FILE" | cut -d: -f2 || echo "")
    
    if [ -n "$ON_DEMAND_PID" ]; then
        if ps -p "$ON_DEMAND_PID" > /dev/null 2>&1; then
            kill "$ON_DEMAND_PID" 2>/dev/null || true
            sleep 1
            echo -e "${GREEN}  ✓ Stopped previous on-demand mock${NC}"
        fi
        # Remove on-demand entry from PID file
        grep -v "^on-demand:" "$PID_FILE" > "$PID_FILE.tmp" || true
        mv "$PID_FILE.tmp" "$PID_FILE"
    else
        echo -e "${YELLOW}  No on-demand mock running${NC}"
    fi
fi

echo ""

# Start new on-demand mock
echo -e "${YELLOW}[2/2] Starting $DOMAIN on port $ON_DEMAND_PORT...${NC}"

# Ensure port is free
if lsof -ti tcp:"$ON_DEMAND_PORT" > /dev/null 2>&1; then
    lsof -ti tcp:"$ON_DEMAND_PORT" | xargs -r kill >/dev/null 2>&1 || true
    sleep 1
fi

# Start Prism
npx @stoplight/prism-cli mock "$BUNDLE_FILE" -p "$ON_DEMAND_PORT" -h 0.0.0.0 > "/tmp/prism-on-demand.log" 2>&1 &
PID=$!

# Append to PID file
echo "on-demand:$PID" >> "$PID_FILE"

sleep 2

# Check if running
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ $DOMAIN started (PID: $PID)${NC}"
else
    echo -e "${RED}  ✗ Failed to start $DOMAIN${NC}"
    cat "/tmp/prism-on-demand.log"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}On-Demand Mock Switched${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Current On-Demand Mock:${NC}"
echo "  Domain: $DOMAIN"
echo "  Port:   $ON_DEMAND_PORT"
echo "  URL:    http://localhost:$ON_DEMAND_PORT"
echo ""
echo -e "${YELLOW}To switch to another domain:${NC}"
echo "  bash scripts/switch-mock.sh <domain>"
echo ""

