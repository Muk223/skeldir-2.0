#!/bin/bash
# Test response parity against OpenAPI contracts
# Validates 200 responses, RFC7807 errors, headers, and request validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# UUID regex pattern
UUID_REGEX='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
# ISO 8601 date-time regex (simplified: YYYY-MM-DDTHH:MM:SSZ)
ISO8601_REGEX='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'

# Helper function to check if jq is available
check_jq() {
    if ! command -v jq > /dev/null 2>&1; then
        echo -e "${RED}Error: jq is required for JSON parsing. Please install jq.${NC}"
        exit 1
    fi
}

# Helper function to validate UUID
validate_uuid() {
    local uuid=$1
    if [[ $uuid =~ $UUID_REGEX ]]; then
        return 0
    else
        return 1
    fi
}

# Helper function to validate ISO 8601
validate_iso8601() {
    local timestamp=$1
    if [[ $timestamp =~ $ISO8601_REGEX ]]; then
        return 0
    else
        return 1
    fi
}

# Test counter
test_pass() {
    PASSED=$((PASSED + 1))
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

test_fail() {
    FAILED=$((FAILED + 1))
    echo -e "${RED}✗ FAIL${NC}: $1"
    return 1
}

check_jq

echo -e "${GREEN}=== Testing Response Parity ===${NC}"
echo ""

# Helper function to generate UUID
generate_uuid() {
    if command -v uuidgen > /dev/null 2>&1; then
        uuidgen
    elif command -v powershell > /dev/null 2>&1; then
        powershell -Command "[guid]::NewGuid().ToString()"
    else
        echo "test-$(date +%s)"
    fi
}

# Test 1: Auth login - 200 response schema validation
echo -e "${YELLOW}Test 1: Auth login 200 response schema${NC}"
CORRELATION_ID=$(generate_uuid)
RESPONSE=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -d '{"email":"test@example.com","password":"test"}')

HTTP_CODE=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -d '{"email":"test@example.com","password":"test"}' \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token // empty')
    REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token // empty')
    EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in // empty')
    TOKEN_TYPE=$(echo "$RESPONSE" | jq -r '.token_type // empty')
    
    if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ] && \
       [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ] && \
       [ -n "$EXPIRES_IN" ] && [ "$EXPIRES_IN" != "null" ] && [ "$EXPIRES_IN" -gt 0 ] && \
       [ "$TOKEN_TYPE" = "Bearer" ]; then
        test_pass "Auth login contains all required fields with correct types"
    else
        test_fail "Auth login missing required fields or incorrect types"
        echo "  access_token: $ACCESS_TOKEN"
        echo "  refresh_token: $REFRESH_TOKEN"
        echo "  expires_in: $EXPIRES_IN"
        echo "  token_type: $TOKEN_TYPE"
    fi
else
    test_fail "Auth login returned HTTP $HTTP_CODE instead of 200"
fi

# Test 2: Attribution realtime - 200 response schema validation
echo -e "${YELLOW}Test 2: Attribution realtime 200 response schema${NC}"
CORRELATION_ID=$(generate_uuid)
RESPONSE=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID")

HTTP_CODE=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_REVENUE=$(echo "$RESPONSE" | jq -r '.total_revenue // empty')
    VERIFIED=$(echo "$RESPONSE" | jq -r '.verified // empty')
    DATA_FRESHNESS=$(echo "$RESPONSE" | jq -r '.data_freshness_seconds // empty')
    TENANT_ID=$(echo "$RESPONSE" | jq -r '.tenant_id // empty')
    
    if [ -n "$TOTAL_REVENUE" ] && [ "$TOTAL_REVENUE" != "null" ] && \
       [ -n "$VERIFIED" ] && [ "$VERIFIED" != "null" ] && \
       [ -n "$DATA_FRESHNESS" ] && [ "$DATA_FRESHNESS" != "null" ] && \
       [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ] && validate_uuid "$TENANT_ID"; then
        test_pass "Attribution realtime contains all required fields with correct types"
    else
        test_fail "Attribution realtime missing required fields or incorrect types"
        echo "  total_revenue: $TOTAL_REVENUE"
        echo "  verified: $VERIFIED"
        echo "  data_freshness_seconds: $DATA_FRESHNESS"
        echo "  tenant_id: $TENANT_ID"
    fi
else
    test_fail "Attribution realtime returned HTTP $HTTP_CODE instead of 200"
fi

# Test 3: Health - 200 response schema validation
echo -e "${YELLOW}Test 3: Health 200 response schema${NC}"
RESPONSE=$(curl -s http://localhost:4014/api/health)
HTTP_CODE=$(curl -s http://localhost:4014/api/health -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(echo "$RESPONSE" | jq -r '.status // empty')
    TIMESTAMP=$(echo "$RESPONSE" | jq -r '.timestamp // empty')
    
    if [ "$STATUS" = "healthy" ] && [ -n "$TIMESTAMP" ] && [ "$TIMESTAMP" != "null" ] && validate_iso8601 "$TIMESTAMP"; then
        test_pass "Health contains status='healthy' and timestamp in ISO 8601 format"
    else
        test_fail "Health missing required fields or incorrect format"
        echo "  status: $STATUS"
        echo "  timestamp: $TIMESTAMP"
    fi
else
    test_fail "Health returned HTTP $HTTP_CODE instead of 200"
fi

# Test 4: Reconciliation status - 200 response schema validation
echo -e "${YELLOW}Test 4: Reconciliation status 200 response schema${NC}"
CORRELATION_ID=$(generate_uuid)
RESPONSE=$(curl -s http://localhost:4012/api/reconciliation/status \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID")

HTTP_CODE=$(curl -s http://localhost:4012/api/reconciliation/status \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    STATE=$(echo "$RESPONSE" | jq -r '.state // empty')
    LAST_RUN_AT=$(echo "$RESPONSE" | jq -r '.last_run_at // empty')
    TENANT_ID=$(echo "$RESPONSE" | jq -r '.tenant_id // empty')
    
    if [ -n "$STATE" ] && [ "$STATE" != "null" ] && \
       [[ "$STATE" =~ ^(idle|running|failed|completed)$ ]] && \
       [ -n "$LAST_RUN_AT" ] && [ "$LAST_RUN_AT" != "null" ] && validate_iso8601 "$LAST_RUN_AT" && \
       [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ] && validate_uuid "$TENANT_ID"; then
        test_pass "Reconciliation status contains all required fields with correct types"
    else
        test_fail "Reconciliation status missing required fields or incorrect types"
        echo "  state: $STATE"
        echo "  last_run_at: $LAST_RUN_AT"
        echo "  tenant_id: $TENANT_ID"
    fi
else
    test_fail "Reconciliation status returned HTTP $HTTP_CODE instead of 200"
fi

# Test 5: Export revenue - 200 response schema validation
echo -e "${YELLOW}Test 5: Export revenue 200 response schema${NC}"
CORRELATION_ID=$(generate_uuid)
RESPONSE=$(curl -s "http://localhost:4013/api/export/revenue?format=json" \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID")

HTTP_CODE=$(curl -s "http://localhost:4013/api/export/revenue?format=json" \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $CORRELATION_ID" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    FILE_URL=$(echo "$RESPONSE" | jq -r '.file_url // empty')
    TENANT_ID=$(echo "$RESPONSE" | jq -r '.tenant_id // empty')
    
    # Basic URI validation (starts with http:// or https://)
    URI_REGEX='^https?://'
    
    if [ -n "$FILE_URL" ] && [ "$FILE_URL" != "null" ] && [[ $FILE_URL =~ $URI_REGEX ]] && \
       [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ] && validate_uuid "$TENANT_ID"; then
        test_pass "Export revenue contains all required fields with correct types"
    else
        test_fail "Export revenue missing required fields or incorrect types"
        echo "  file_url: $FILE_URL"
        echo "  tenant_id: $TENANT_ID"
    fi
else
    test_fail "Export revenue returned HTTP $HTTP_CODE instead of 200"
fi

# Test 6: 401 Unauthorized - RFC7807 Problem schema validation
echo -e "${YELLOW}Test 6: 401 Unauthorized RFC7807 Problem schema${NC}"
RESPONSE=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "X-Correlation-ID: $(generate_uuid)")

HTTP_CODE=$(curl -s http://localhost:4011/api/attribution/revenue/realtime \
    -H "X-Correlation-ID: $(generate_uuid)" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "401" ]; then
    TYPE=$(echo "$RESPONSE" | jq -r '.type // empty')
    TITLE=$(echo "$RESPONSE" | jq -r '.title // empty')
    STATUS=$(echo "$RESPONSE" | jq -r '.status // empty')
    DETAIL=$(echo "$RESPONSE" | jq -r '.detail // empty')
    ERROR_ID=$(echo "$RESPONSE" | jq -r '.error_id // empty')
    CORRELATION_ID=$(echo "$RESPONSE" | jq -r '.correlation_id // empty')
    
    URI_REGEX='^https?://'
    
    if [ -n "$TYPE" ] && [ "$TYPE" != "null" ] && [[ $TYPE =~ $URI_REGEX ]] && \
       [ -n "$TITLE" ] && [ "$TITLE" != "null" ] && [ "$TITLE" != "" ] && \
       [ "$STATUS" = "401" ] && \
       [ -n "$DETAIL" ] && [ "$DETAIL" != "null" ] && [ "$DETAIL" != "" ] && \
       [ -n "$ERROR_ID" ] && [ "$ERROR_ID" != "null" ] && validate_uuid "$ERROR_ID" && \
       [ -n "$CORRELATION_ID" ] && [ "$CORRELATION_ID" != "null" ] && validate_uuid "$CORRELATION_ID"; then
        test_pass "401 error response matches RFC7807 Problem schema with Skeldir extensions"
    else
        test_fail "401 error response missing required RFC7807 fields or Skeldir extensions"
        echo "  type: $TYPE"
        echo "  title: $TITLE"
        echo "  status: $STATUS"
        echo "  detail: $DETAIL"
        echo "  error_id: $ERROR_ID"
        echo "  correlation_id: $CORRELATION_ID"
    fi
else
    test_fail "Expected 401 Unauthorized, got HTTP $HTTP_CODE"
fi

# Test 7: 429 Too Many Requests - Rate limit headers
echo -e "${YELLOW}Test 7: 429 Too Many Requests with rate limit headers${NC}"
RESPONSE_HEADERS=$(curl -s -I -X GET http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $(generate_uuid)" \
    -H "Prefer: code=429")

HTTP_CODE=$(curl -s -X GET http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $(generate_uuid)" \
    -H "Prefer: code=429" \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "429" ]; then
    RATE_LIMIT_LIMIT=$(echo "$RESPONSE_HEADERS" | grep -i "X-RateLimit-Limit" | cut -d' ' -f2 | tr -d '\r')
    RATE_LIMIT_REMAINING=$(echo "$RESPONSE_HEADERS" | grep -i "X-RateLimit-Remaining" | cut -d' ' -f2 | tr -d '\r')
    RATE_LIMIT_RESET=$(echo "$RESPONSE_HEADERS" | grep -i "X-RateLimit-Reset" | cut -d' ' -f2 | tr -d '\r')
    
    if [ -n "$RATE_LIMIT_LIMIT" ] && [ -n "$RATE_LIMIT_REMAINING" ] && [ -n "$RATE_LIMIT_RESET" ]; then
        test_pass "429 error response includes rate limit headers"
    else
        test_fail "429 error response missing rate limit headers"
        echo "  X-RateLimit-Limit: $RATE_LIMIT_LIMIT"
        echo "  X-RateLimit-Remaining: $RATE_LIMIT_REMAINING"
        echo "  X-RateLimit-Reset: $RATE_LIMIT_RESET"
    fi
else
    test_fail "Expected 429 Too Many Requests, got HTTP $HTTP_CODE"
fi

# Test 8: X-Correlation-ID header propagation
echo -e "${YELLOW}Test 8: X-Correlation-ID header propagation${NC}"
REQUEST_CORRELATION_ID=$(generate_uuid)
RESPONSE_HEADERS=$(curl -s -I http://localhost:4011/api/attribution/revenue/realtime \
    -H "Authorization: Bearer mock-token" \
    -H "X-Correlation-ID: $REQUEST_CORRELATION_ID")

RESPONSE_CORRELATION_ID=$(echo "$RESPONSE_HEADERS" | grep -i "X-Correlation-ID" | cut -d' ' -f2 | tr -d '\r')

if [ -n "$RESPONSE_CORRELATION_ID" ] && [ "$RESPONSE_CORRELATION_ID" = "$REQUEST_CORRELATION_ID" ]; then
    test_pass "X-Correlation-ID header propagated correctly"
else
    test_fail "X-Correlation-ID header not propagated or mismatch"
    echo "  Request: $REQUEST_CORRELATION_ID"
    echo "  Response: $RESPONSE_CORRELATION_ID"
fi

# Test 9: Request validation - missing required field
echo -e "${YELLOW}Test 9: Request validation (missing required field)${NC}"
RESPONSE=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: $(generate_uuid)" \
    -d '{"email":"test@example.com"}')

HTTP_CODE=$(curl -s -X POST http://localhost:4010/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: $(generate_uuid)" \
    -d '{"email":"test@example.com"}' \
    -w "\n%{http_code}" | tail -1)

if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "422" ]; then
    TYPE=$(echo "$RESPONSE" | jq -r '.type // empty')
    STATUS=$(echo "$RESPONSE" | jq -r '.status // empty')
    
    URI_REGEX='^https?://'
    
    if [ -n "$TYPE" ] && [ "$TYPE" != "null" ] && [[ $TYPE =~ $URI_REGEX ]] && \
       [ "$STATUS" = "$HTTP_CODE" ]; then
        test_pass "Request validation works (missing required field returns $HTTP_CODE with RFC7807 Problem schema)"
    else
        test_fail "Request validation returned $HTTP_CODE but missing RFC7807 Problem schema"
    fi
else
    test_fail "Request validation expected 400/422, got HTTP $HTTP_CODE"
fi

# Summary
echo ""
echo -e "${GREEN}=== Test Summary ===${NC}"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi

