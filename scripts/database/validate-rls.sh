#!/usr/bin/env bash
# Validate row-level security policies using canonical seed data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/backend/validation/evidence/database"
LOG_FILE="$EVIDENCE_DIR/rls_validation.txt"

source "$SCRIPT_DIR/lib_guardrail_fixture.sh"

DATABASE_URL="${1:-${DATABASE_URL:-}}"
if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL not provided" >&2
    echo "Usage: $0 [DATABASE_URL]" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_DIR"
exec > >(tee "$LOG_FILE") 2>&1

timestamp() { date --iso-8601=seconds; }

echo "=========================================="
echo "RLS Validation ($(timestamp))"
echo "=========================================="
echo ""

seed_guardrail_fixture "$DATABASE_URL"
trap 'cleanup_guardrail_fixture "$DATABASE_URL"' EXIT

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

# Create a second tenant to simulate another customer context
SECOND_TENANT_ID=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "
    INSERT INTO tenants (id, name, api_key_hash, notification_email)
    VALUES (gen_random_uuid(), 'rls_secondary_tenant', md5(clock_timestamp()::text), 'rls-secondary@example.com')
    RETURNING id;
")
SECOND_TENANT_ID=$(echo "$SECOND_TENANT_ID" | head -n 1 | tr -d $'\r')

echo "Test 1: RLS allows tenant-scoped read"
tenant_count=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At <<SQL
SET ROLE app_rw;
SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
SELECT COUNT(*) FROM attribution_events WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;
SQL
)
tenant_count=$(echo "$tenant_count" | tail -n 1 | tr -d '\r')
if [[ "$tenant_count" -eq 1 ]]; then
    pass "Tenant context can read its own attribution event"
else
    fail "Tenant context could not read its own data"
fi
echo ""

echo "Test 2: RLS blocks cross-tenant read"
cross_count=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At <<SQL
SET ROLE app_rw;
SET app.current_tenant_id = '$SECOND_TENANT_ID';
SELECT COUNT(*) FROM attribution_events WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;
SQL
)
cross_count=$(echo "$cross_count" | tail -n 1 | tr -d '\r')
if [[ "$cross_count" -eq 0 ]]; then
    pass "Cross-tenant read blocked by RLS"
else
    fail "RLS allowed cross-tenant read"
fi
echo ""

echo "Test 3: RLS WITH CHECK blocks tenant spoofing on insert"
spoof_attempt=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
    SET ROLE app_rw;
    SET app.current_tenant_id = '$SECOND_TENANT_ID';
    INSERT INTO attribution_events (
        tenant_id,
        session_id,
        correlation_id,
        channel,
        event_type,
        occurred_at,
        event_timestamp,
        idempotency_key,
        raw_payload,
        revenue_cents
    )
    VALUES (
        '$GUARDRAIL_TENANT_ID'::uuid,
        gen_random_uuid(),
        gen_random_uuid(),
        'organic',
        'purchase',
        NOW(),
        NOW(),
        md5(random()::text),
        jsonb_build_object('order_id','ORD-RLS','source','fixture'),
        3333
    );
" 2>&1 || true)
if grep -qi "violates row-level security policy" <<<"$spoof_attempt"; then
    pass "RLS WITH CHECK prevented tenant spoofing insert"
else
    fail "RLS WITH CHECK did not block tenant spoofing insert"
fi
echo ""

echo "Cleaning up secondary tenant..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 >/dev/null <<SQL
DELETE FROM tenants WHERE id = '$SECOND_TENANT_ID'::uuid;
SQL

echo "=========================================="
echo "RLS validation complete ($(timestamp))"
echo "Evidence written to $LOG_FILE"
echo "=========================================="
