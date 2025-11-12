#!/bin/bash
# Measure p95 latency for health endpoints
# Probes /api/health endpoint 100 times and calculates 95th percentile

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Measuring Latency ===${NC}"

# Health service endpoint
HEALTH_URL="http://localhost:4014/api/health"
NUM_REQUESTS=100
TARGET_P95_MS=500

echo -e "${YELLOW}Probing $HEALTH_URL $NUM_REQUESTS times...${NC}"

# Array to store response times
TIMES=()

# Make requests and collect response times
for i in $(seq 1 $NUM_REQUESTS); do
    TIME=$(curl -s -o /dev/null -w "%{time_total}" "$HEALTH_URL" 2>/dev/null)
    # Convert to milliseconds (multiply by 1000) - use awk for portability
    TIME_MS=$(echo "$TIME" | awk '{printf "%.2f", $1 * 1000}')
    TIMES+=("$TIME_MS")
    
    # Progress indicator
    if [ $((i % 10)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""

# Sort times numerically using awk for portability
SORTED_TIMES=($(printf '%s\n' "${TIMES[@]}" | sort -n))

# Calculate p95 (95th percentile)
# p95 index = ceil(0.95 * n) - 1 (0-indexed)
NUM_TIMES=${#SORTED_TIMES[@]}
P95_INDEX=$(( ($NUM_TIMES * 95 + 99) / 100 ))
P95_INDEX=$((P95_INDEX - 1))

# Ensure index is within bounds
if [ $P95_INDEX -ge $NUM_TIMES ]; then
    P95_INDEX=$((NUM_TIMES - 1))
fi

P95_MS=${SORTED_TIMES[$P95_INDEX]}

# Format p95 to 2 decimal places
P95_MS=$(echo "$P95_MS" | awk '{printf "%.2f", $1}')

echo -e "${GREEN}Latency measurements complete${NC}"
echo "  Total requests: $NUM_REQUESTS"
echo "  p95 latency: ${P95_MS}ms"
echo "  Target: < ${TARGET_P95_MS}ms"

# Check if p95 meets requirement using awk for portability
PASS=false
if [ -n "$P95_MS" ]; then
    COMPARE=$(echo "$P95_MS" | awk -v target="$TARGET_P95_MS" '{if ($1+0 < target) print "true"; else print "false"}')
    if [ "$COMPARE" = "true" ]; then
        PASS=true
    fi
fi

# Create JSON report
REPORT_FILE="mocks-latency-report.json"
cat > "$REPORT_FILE" <<EOF
{
  "service": "health",
  "p95_ms": $P95_MS,
  "pass": $PASS,
  "target_ms": $TARGET_P95_MS,
  "requests": $NUM_REQUESTS
}
EOF

echo ""
if [ "$PASS" = "true" ]; then
    echo -e "${GREEN}✓ PASS: p95 latency ($P95_MS ms) is below target ($TARGET_P95_MS ms)${NC}"
    echo "Report saved to: $REPORT_FILE"
    exit 0
else
    echo -e "${RED}✗ FAIL: p95 latency ($P95_MS ms) exceeds target ($TARGET_P95_MS ms)${NC}"
    echo "Report saved to: $REPORT_FILE"
    exit 1
fi

