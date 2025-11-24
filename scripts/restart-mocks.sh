#!/bin/bash
# Restart Replit-Native Mock Servers
# Convenience script: stop + start

set -e

# Colors
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Restarting mock servers...${NC}"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop
bash "$SCRIPT_DIR/stop-mocks.sh"

# Brief pause
sleep 1

# Start
bash "$SCRIPT_DIR/start-mocks.sh"
