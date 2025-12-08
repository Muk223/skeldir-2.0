#!/usr/bin/env bash
# Validate database-level PII guardrails against the current schema.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/backend/validation/evidence/database"
LOG_FILE="$EVIDENCE_DIR/pii_guardrail_validation.txt"

source "$SCRIPT_DIR/lib_guardrail_fixture.sh"

DATABASE_URL="${1:-${DATABASE_URL:-}}"
if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL not provided" >&2
    echo "Usage: $0 [DATABASE_URL]" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_DIR"
exec > >(tee "$LOG_FILE") 2>&1

timestamp() {
    date --iso-8601=seconds
}

echo "=========================================="
echo "PII Guardrail Validation Test ($(timestamp))"
echo "=========================================="
echo ""

seed_guardrail_fixture "$DATABASE_URL"
trap 'cleanup_guardrail_fixture "$DATABASE_URL"' EXIT

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

# Test 1: attribution_events.raw_payload with PII key should fail
echo "Test 1: Attribution event insert with PII key 'email' (expect FAILURE)"
pii_event_output=$(
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
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
        ) VALUES (
            '$GUARDRAIL_TENANT_ID'::uuid,
            gen_random_uuid(),
            gen_random_uuid(),
            'organic',
            'purchase',
            NOW(),
            NOW(),
            md5(random()::text),
            '{\"order_id\":\"ORD-PII\",\"email\":\"blocked@example.com\"}'::jsonb,
            5000,
            5000
        );
    " 2>&1 || true
)
echo "$pii_event_output"
if grep -qi "PII key detected" <<<"$pii_event_output"; then
    pass "PII trigger blocked attribution_events insert with PII key"
else
    fail "PII trigger did not block attribution_events insert with PII key"
fi
echo ""

# Test 2: attribution_events.raw_payload with PII only in value should pass
echo "Test 2: Attribution event insert with PII-like value (expect SUCCESS)"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 >/dev/null <<SQL
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
) VALUES (
    '$GUARDRAIL_TENANT_ID'::uuid,
    gen_random_uuid(),
    gen_random_uuid(),
    'organic',
    'purchase',
    NOW(),
    NOW(),
    md5(random()::text),
    jsonb_build_object('order_id','ORD-NO-PII','notes','contact ops@example.com'),
    4200,
    4200
);
SQL
pass "Attribution event with PII only in value succeeded (documented limitation)"
echo ""

# Helper: insert ledger row with custom metadata
insert_ledger_with_metadata() {
    local metadata_json="$1"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
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
                'direct',
                'purchase',
                NOW(),
                NOW(),
                md5(random()::text),
                jsonb_build_object('order_id','ORD-LEDGER','source','fixture'),
                1000,
                1000
            )
            RETURNING id, tenant_id
        ),
        new_alloc AS (
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
                confidence_score,
                verified
            )
            SELECT
                event_seed.tenant_id,
                event_seed.id,
                'direct',
                1000,
                jsonb_build_object('model','bayesian_mmm'),
                gen_random_uuid(),
                1.0,
                concat('fixture-', substr(md5(random()::text), 1, 6)),
                'bayesian_mmm',
                0.950,
                FALSE
            FROM event_seed
            RETURNING id, tenant_id
        )
        INSERT INTO revenue_ledger (
            tenant_id,
            allocation_id,
            revenue_cents,
            amount_cents,
            is_verified,
            verified_at,
            posted_at,
            transaction_id,
            order_id,
            state,
            previous_state,
            verification_source,
            verification_timestamp,
            metadata,
            currency
        )
        SELECT
            new_alloc.tenant_id,
            new_alloc.id,
            1000,
            1000,
            TRUE,
            NOW(),
            NOW(),
            concat('txn-pii-', substr(md5(random()::text), 1, 12)),
            'ORD-LEDGER-PII',
            'captured',
            'authorized',
            'auto',
            NOW(),
            $metadata_json,
            'USD'
        FROM new_alloc;
    " 2>&1
}

# Test 3: revenue_ledger.metadata with PII key should fail
echo "Test 3: Revenue ledger metadata with PII key 'email' (expect FAILURE)"
pii_ledger_output=$(insert_ledger_with_metadata "'{\"processor\":\"stripe\",\"email\":\"finance@example.com\"}'::jsonb" 2>&1 || true)
echo "$pii_ledger_output"
if grep -qi "PII key detected" <<<"$pii_ledger_output"; then
    pass "PII trigger blocked revenue_ledger metadata containing PII key"
else
    fail "PII trigger did not block revenue_ledger metadata containing PII key"
fi
echo ""

# Test 4: revenue_ledger.metadata NULL allowed
echo "Test 4: Revenue ledger insert with NULL metadata (expect SUCCESS)"
if null_output=$(insert_ledger_with_metadata "NULL" 2>&1); then
    pass "Revenue ledger insert with NULL metadata succeeded"
else
    echo "$null_output"
    fail "Revenue ledger insert with NULL metadata failed unexpectedly"
fi
echo ""

echo "=========================================="
echo "PII guardrail validation complete ($(timestamp))"
echo "Evidence written to $LOG_FILE"
echo "=========================================="
