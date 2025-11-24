#!/bin/bash
# Stop Replit-Native Mock Servers
# Gracefully terminates Prism mock server processes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping SKELDIR 2.0 Mock Servers...${NC}"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$ROOT_DIR/.mocks.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}No running mocks found (PID file missing)${NC}"
    echo -e "${YELLOW}If mocks are running, find PIDs manually: ps aux | grep prism${NC}"
    exit 0
fi

# Read PIDs and kill processes
STOPPED_COUNT=0
FAILED_COUNT=0

while IFS=: read -r MOCK_ID PID; do
    if [ -z "$PID" ]; then
        continue
    fi
    
    echo -e "Stopping ${MOCK_ID} (PID: $PID)..."
    
    # Check if process exists
    if ps -p "$PID" > /dev/null 2>&1; then
        # Try graceful termination first (SIGTERM)
        kill "$PID" 2>/dev/null || true
        sleep 1
        
        # Check if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            # Force kill (SIGKILL)
            echo -e "${YELLOW}  Process still running, forcing shutdown...${NC}"
            kill -9 "$PID" 2>/dev/null || true
            sleep 1
        fi
        
        # Final check
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${RED}  ✗ Failed to stop ${MOCK_ID}${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        else
            echo -e "${GREEN}  ✓ Stopped ${MOCK_ID}${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
        fi
    else
        echo -e "${YELLOW}  Process not running (already stopped)${NC}"
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    fi
done < "$PID_FILE"

# Remove PID file
rm -f "$PID_FILE"
echo ""

# Summary
if [ $FAILED_COUNT -eq 0 ]; then
    echo -e "${GREEN}Successfully stopped $STOPPED_COUNT mock server(s)${NC}"
    exit 0
else
    echo -e "${RED}Stopped $STOPPED_COUNT, failed to stop $FAILED_COUNT${NC}"
    echo -e "${YELLOW}Check running processes: ps aux | grep prism${NC}"
    exit 1
fi
