#!/bin/bash
# Stop all SKELDIR mock servers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping SKELDIR mock servers...${NC}"

# Stop services
docker-compose -f docker-compose.yml down

# Verify all containers stopped
RUNNING=$(docker-compose -f docker-compose.yml ps --services 2>/dev/null | wc -l)

if [ "$RUNNING" -eq 0 ]; then
    echo -e "${GREEN}All mock servers stopped successfully${NC}"
    exit 0
else
    echo -e "${RED}Warning: Some containers may still be running${NC}"
    docker-compose -f docker-compose.yml ps
    exit 1
fi


