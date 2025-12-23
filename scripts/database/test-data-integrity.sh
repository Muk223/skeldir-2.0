#!/usr/bin/env bash
# Validate data integrity guardrails: RLS, immutability, idempotency, sum-equality.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/backend/validation/evidence/database"
LOG_FILE="$EVIDENCE_DIR/integrity_validation.txt"

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
echo "Data Integrity Controls Validation ($(timestamp))"
echo "=========================================="
echo ""

seed_guardrail_fixture "$DATABASE_URL"
trap 'cleanup_guardrail_fixture "$DATABASE_URL"' EXIT

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

# Helper to run SQL and capture first column
run_scalar() {
    local sql="$1"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "$sql"
}

run_with_tenant() {
    local tenant_id="$1"
    local sql="$2"
    local output
    output=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At <<SQL
SET app.current_tenant_id = '$tenant_id';
$sql
SQL
)
    echo "$output" | tail -n 1 | tr -d $'\r'
}

# Create an additional tenant for RLS cross-checks
SECOND_TENANT_ID=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "
    INSERT INTO tenants (id, name, api_key_hash, notification_email)
    VALUES (gen_random_uuid(), 'guardrail_fixture_secondary', md5(clock_timestamp()::text), 'guardrail-secondary@example.com')
    RETURNING id;
")
SECOND_TENANT_ID=$(echo "$SECOND_TENANT_ID" | head -n 1 | tr -d $'\r')

echo "Scenario 1: RLS tenant isolation"
tenant_rows=$(run_with_tenant "$GUARDRAIL_TENANT_ID" "SELECT COUNT(*) FROM attribution_events WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;")
other_rows=$(run_with_tenant "$SECOND_TENANT_ID" "SELECT COUNT(*) FROM attribution_events WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;")
if [[ "$tenant_rows" -eq 1 ]]; then
    pass "Tenant context sees its own attribution event"
else
    fail "Tenant context failed to read attribution event"
fi
if [[ "$other_rows" -eq 0 ]]; then
    pass "Cross-tenant context blocked by RLS"
else
    fail "RLS allowed cross-tenant read"
fi
echo ""

echo "Scenario 2: Immutability guardrails on attribution_events"
immut_update=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
    SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
    UPDATE attribution_events
    SET revenue_cents = revenue_cents + 1
    WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;
" 2>&1 || true)
if grep -qi "prevent" <<<"$immut_update"; then
    pass "Immutability trigger blocked UPDATE on attribution_events"
else
    fail "UPDATE on attribution_events unexpectedly succeeded"
fi

immut_delete=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
    SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
    DELETE FROM attribution_events WHERE id = '$GUARDRAIL_EVENT_ID'::uuid;
" 2>&1 || true)
if grep -qi "prevent" <<<"$immut_delete"; then
    pass "Immutability trigger blocked DELETE on attribution_events"
else
    fail "DELETE on attribution_events unexpectedly succeeded"
fi
echo ""

echo "Scenario 3: Sum-equality guardrail"
set +e
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
    SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
    INSERT INTO attribution_allocations (
        tenant_id,
        event_id,
        channel_code,
        allocated_revenue_cents,
        model_metadata,
        correlation_id,
        allocation_ratio,
        model_version,
        model_type,
        confidence_score
    )
    VALUES (
        '$GUARDRAIL_TENANT_ID'::uuid,
        '$GUARDRAIL_EVENT_ID'::uuid,
        'facebook_paid',
        2500,
        jsonb_build_object('model','bayesian_mmm'),
        gen_random_uuid(),
        0.25,
        'v1.0.0',
        'bayesian_mmm',
        0.750
    );
"
sum_status=$?
set -e
if [[ $sum_status -ne 0 ]]; then
    pass "Sum-equality trigger blocked drifted allocations"
else
    fail "Sum-equality trigger did not block invalid allocation sum"
fi

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 >/dev/null <<SQL
SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
WITH event_seed AS (
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
        revenue_cents,
        conversion_value_cents
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
        jsonb_build_object('order_id','ORD-VALID','source','fixture'),
        8000,
        8000
    )
    RETURNING id, tenant_id
)
INSERT INTO attribution_allocations (
    tenant_id,
    event_id,
    channel_code,
    allocated_revenue_cents,
    model_metadata,
    allocation_ratio,
    model_version,
    model_type,
    confidence_score
)
SELECT tenant_id, id, vals.channel_code, vals.alloc_value, jsonb_build_object('model','bayesian_mmm'),
       vals.ratio, 'v1.1.0', 'bayesian_mmm', 0.810
FROM event_seed
CROSS JOIN (VALUES
    ('organic', 4800, 0.6),
    ('email', 3200, 0.4)
) AS vals(channel_code, alloc_value, ratio);
SQL
pass "Sum-equality validation allowed balanced allocations"
echo ""

echo "Scenario 4: Idempotency enforcement"
duplicate_event=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
    SET app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
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
        '$GUARDRAIL_EVENT_IDEMPOTENCY_KEY',
        jsonb_build_object('order_id','ORD-DUP','source','fixture'),
        7777
    );
" 2>&1 || true)
if grep -qi "duplicate key value violates unique constraint" <<<"$duplicate_event"; then
    pass "Idempotency constraint rejected duplicate event"
else
    fail "Duplicate idempotency insert unexpectedly succeeded"
fi
echo ""

echo "Cleaning up secondary tenant..."
set +e
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 >/dev/null <<SQL || true
SET app.current_tenant_id = '$SECOND_TENANT_ID';
ALTER TABLE attribution_recompute_jobs DISABLE ROW LEVEL SECURITY;
DELETE FROM attribution_recompute_jobs WHERE tenant_id = '$SECOND_TENANT_ID'::uuid;
ALTER TABLE attribution_recompute_jobs ENABLE ROW LEVEL SECURITY;
DELETE FROM tenants WHERE id = '$SECOND_TENANT_ID'::uuid;
SQL
set -e

echo "=========================================="
echo "Data integrity validation complete ($(timestamp))"
echo "Evidence written to $LOG_FILE"
echo "=========================================="
exit 0
