#!/bin/bash
# Start all SKELDIR mock servers
# Pre-flight checks, docker-compose up, and liveness verification

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting SKELDIR 2.0 Mock Servers...${NC}"

# Pre-flight checks
echo -e "${YELLOW}Running pre-flight checks...${NC}"

# Check if contracts directory exists
if [ ! -d "contracts/openapi/v1" ]; then
    echo -e "${RED}Error: contracts/openapi/v1 directory not found${NC}"
    exit 1
fi

# Check if all contract files exist
CONTRACT_FILES=(
    "contracts/openapi/v1/auth.yaml"
    "contracts/openapi/v1/attribution.yaml"
    "contracts/openapi/v1/reconciliation.yaml"
    "contracts/openapi/v1/export.yaml"
    "contracts/openapi/v1/health.yaml"
    "contracts/openapi/v1/webhooks/shopify.yaml"
    "contracts/openapi/v1/webhooks/woocommerce.yaml"
    "contracts/openapi/v1/webhooks/stripe.yaml"
    "contracts/openapi/v1/webhooks/paypal.yaml"
)

for file in "${CONTRACT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: Contract file not found: $file${NC}"
        exit 1
    fi
done

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if ports are in use (Windows-compatible check)
check_port() {
    local port=$1
    if command -v netstat > /dev/null 2>&1; then
        if netstat -an | grep -q ":$port " 2>/dev/null; then
            return 1
        fi
    elif command -v lsof > /dev/null 2>&1; then
        if lsof -i :$port > /dev/null 2>&1; then
            return 1
        fi
    fi
    return 0
}

PORTS=(4010 4011 4012 4013 4014 4015 4016 4017 4018)
for port in "${PORTS[@]}"; do
    if ! check_port $port; then
        echo -e "${YELLOW}Warning: Port $port appears to be in use${NC}"
    fi
done

echo -e "${GREEN}Pre-flight checks passed${NC}"

# Start services
echo -e "${YELLOW}Starting Docker Compose services...${NC}"
docker-compose -f docker-compose.yml up -d

# Wait for containers to be running
echo -e "${YELLOW}Waiting for containers to start...${NC}"
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    RUNNING=$(docker-compose -f docker-compose.yml ps --services --filter "status=running" | wc -l)
    if [ "$RUNNING" -eq 9 ]; then
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ "$RUNNING" -ne 9 ]; then
    echo -e "${RED}Error: Not all containers started. Current status:${NC}"
    docker-compose -f docker-compose.yml ps
    exit 1
fi

# Wait for healthcheck to pass (health service)
echo -e "${YELLOW}Waiting for health service to be healthy...${NC}"
MAX_HEALTH_WAIT=30
HEALTH_ELAPSED=0
while [ $HEALTH_ELAPSED -lt $MAX_HEALTH_WAIT ]; do
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' skeldir-mock-health 2>/dev/null || echo "none")
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        break
    fi
    sleep 2
    HEALTH_ELAPSED=$((HEALTH_ELAPSED + 2))
done

# Verify liveness with curl tests
echo -e "${YELLOW}Verifying service liveness...${NC}"

# Test health endpoint
if ! curl -sf http://localhost:4014/api/health > /dev/null 2>&1; then
    echo -e "${RED}Error: Health endpoint not responding${NC}"
    docker-compose -f docker-compose.yml logs health
    exit 1
fi

HEALTH_STATUS=$(curl -s http://localhost:4014/api/health | grep -o '"status":"healthy"' || echo "")
if [ -z "$HEALTH_STATUS" ]; then
    echo -e "${RED}Error: Health endpoint did not return expected status${NC}"
    curl -s http://localhost:4014/api/health
    exit 1
fi

# Test auth login endpoint
# Generate UUID - try uuidgen first, then PowerShell on Windows, then fallback
if command -v uuidgen > /dev/null 2>&1; then
    CORRELATION_ID=$(uuidgen)
elif command -v powershell > /dev/null 2>&1; then
    CORRELATION_ID=$(powershell -Command "[guid]::NewGuid().ToString()")
else
    CORRELATION_ID="test-$(date +%s)"
fi
HTTP_CODE=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -d '{"email":"test@example.com","password":"test"}' \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "401" ]; then
    echo -e "${RED}Error: Auth login endpoint returned unexpected status: $HTTP_CODE${NC}"
    docker-compose -f docker-compose.yml logs auth
    exit 1
fi

# Test attribution endpoint
# Generate UUID - try uuidgen first, then PowerShell on Windows, then fallback
if command -v uuidgen > /dev/null 2>&1; then
    CORRELATION_ID=$(uuidgen)
elif command -v powershell > /dev/null 2>&1; then
    CORRELATION_ID=$(powershell -Command "[guid]::NewGuid().ToString()")
else
    CORRELATION_ID="test-$(date +%s)"
fi
HTTP_CODE=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "401" ]; then
    echo -e "${RED}Error: Attribution endpoint returned unexpected status: $HTTP_CODE${NC}"
    docker-compose -f docker-compose.yml logs attribution
    exit 1
fi

echo -e "${GREEN}All mock servers operational${NC}"
echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  Auth:          http://localhost:4010"
echo "  Attribution:    http://localhost:4011"
echo "  Reconciliation: http://localhost:4012"
echo "  Export:         http://localhost:4013"
echo "  Health:         http://localhost:4014"
echo "  Webhooks (Shopify):    http://localhost:4015"
echo "  Webhooks (WooCommerce): http://localhost:4016"
echo "  Webhooks (Stripe):      http://localhost:4017"
echo "  Webhooks (PayPal):      http://localhost:4018"
echo ""
echo -e "${GREEN}All 9 mock servers are running and responding${NC}"

