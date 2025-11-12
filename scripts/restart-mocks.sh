#!/bin/bash
# Restart mock services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 [service-name|all]"
    echo ""
    echo "Available services:"
    echo "  auth, attribution, reconciliation, export, health"
    echo "  webhooks-shopify, webhooks-woocommerce, webhooks-stripe, webhooks-paypal"
    echo "  all (restarts all services)"
    exit 1
fi

if [ "$SERVICE" = "all" ]; then
    echo -e "${YELLOW}Restarting all mock services...${NC}"
    docker-compose -f docker-compose.yml restart
    
    echo -e "${YELLOW}Waiting for services to be Up...${NC}"
    sleep 5
    
    # Verify all services are Up
    RUNNING=$(docker-compose -f docker-compose.yml ps --services --filter "status=running" | wc -l)
    if [ "$RUNNING" -eq 9 ]; then
        echo -e "${GREEN}All services restarted successfully${NC}"
        docker-compose -f docker-compose.yml ps
        exit 0
    else
        echo -e "${RED}Warning: Not all services are running. Current status:${NC}"
        docker-compose -f docker-compose.yml ps
        exit 1
    fi
fi

# Map service names
case "$SERVICE" in
    auth|attribution|reconciliation|export|health|webhooks-shopify|webhooks-woocommerce|webhooks-stripe|webhooks-paypal)
        SERVICE_NAME="$SERVICE"
        ;;
    shopify)
        SERVICE_NAME="webhooks-shopify"
        ;;
    woocommerce)
        SERVICE_NAME="webhooks-woocommerce"
        ;;
    stripe)
        SERVICE_NAME="webhooks-stripe"
        ;;
    paypal)
        SERVICE_NAME="webhooks-paypal"
        ;;
    *)
        echo -e "${RED}Error: Unknown service: $SERVICE${NC}"
        echo "Available services: auth, attribution, reconciliation, export, health, webhooks-shopify, webhooks-woocommerce, webhooks-stripe, webhooks-paypal, all"
        exit 1
        ;;
esac

echo -e "${YELLOW}Restarting $SERVICE_NAME...${NC}"
docker-compose -f docker-compose.yml restart "$SERVICE_NAME"

echo -e "${YELLOW}Waiting for service to be Up...${NC}"
sleep 3

# Verify service is Up
STATUS=$(docker-compose -f docker-compose.yml ps --format json "$SERVICE_NAME" | grep -o '"State":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" = "running" ]; then
    echo -e "${GREEN}Service $SERVICE_NAME restarted successfully${NC}"
    docker-compose -f docker-compose.yml ps "$SERVICE_NAME"
    exit 0
else
    echo -e "${RED}Warning: Service $SERVICE_NAME status is: $STATUS${NC}"
    docker-compose -f docker-compose.yml ps "$SERVICE_NAME"
    exit 1
fi


