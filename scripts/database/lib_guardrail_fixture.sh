#!/usr/bin/env bash
# Shared helper for database guardrail validations.
# Provides canonical seed data representing a full ingestion path
# (tenant -> attribution_event -> allocations -> revenue_ledger).

set -euo pipefail

# shellcheck disable=SC2034
seed_guardrail_fixture() {
    local database_url="$1"
    local sql="
WITH tenant_seed AS (
    INSERT INTO tenants (id, name, api_key_hash, notification_email)
    VALUES (
        gen_random_uuid(),
        'guardrail_fixture',
        md5(clock_timestamp()::text),
        'guardrail-fixture@example.com'
    )
    RETURNING id
),
set_tenant AS (
    SELECT set_config('app.current_tenant_id', tenant_seed.id::text, false) AS ignored
    FROM tenant_seed
),
event_seed AS (
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
    SELECT
        tenant_seed.id,
        gen_random_uuid(),
        gen_random_uuid(),
        'organic',
        'purchase',
        NOW(),
        NOW(),
        md5(random()::text),
        jsonb_build_object('order_id', 'ORD-GUARDRAIL', 'source', 'fixture'),
        10000,
        10000
    FROM tenant_seed, set_tenant
    RETURNING id, tenant_id, idempotency_key
),
allocation_primary AS (
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
        credible_interval_lower_cents,
        credible_interval_upper_cents,
        verified
    )
    SELECT
        event_seed.tenant_id,
        event_seed.id,
        'organic',
        6000,
        jsonb_build_object('model', 'bayesian_mmm'),
        gen_random_uuid(),
        0.6,
        'v1.0.0',
        'bayesian_mmm',
        0.930,
        5800,
        6200,
        TRUE
    FROM event_seed
    RETURNING id, tenant_id, event_id
),
allocation_secondary AS (
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
        'email',
        4000,
        jsonb_build_object('model', 'bayesian_mmm'),
        gen_random_uuid(),
        0.4,
        'v1.0.0',
        'bayesian_mmm',
        0.870,
        TRUE
    FROM event_seed
),
ledger_seed AS (
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
        allocation_primary.tenant_id,
        allocation_primary.id,
        10000,
        10000,
        TRUE,
        NOW(),
        NOW(),
        concat('txn-', substr(md5(random()::text), 1, 18)),
        'ORD-GUARDRAIL',
        'captured',
        'authorized',
        'auto',
        NOW(),
        jsonb_build_object('variance', 'low', 'source', 'fixture'),
        'USD'
    FROM allocation_primary
    RETURNING id, tenant_id
)
SELECT
    tenant_seed.id,
    event_seed.id,
    event_seed.idempotency_key,
    allocation_primary.id,
    ledger_seed.id
FROM tenant_seed, event_seed, allocation_primary, ledger_seed;
"
    local result
    result=$(psql "$database_url" -v ON_ERROR_STOP=1 -At -F '|' -c "$sql")
    if [[ -z "$result" ]]; then
        echo "Failed to seed guardrail fixture" >&2
        exit 1
    fi
    IFS='|' read -r GUARDRAIL_TENANT_ID GUARDRAIL_EVENT_ID GUARDRAIL_EVENT_IDEMPOTENCY_KEY GUARDRAIL_ALLOCATION_ID GUARDRAIL_LEDGER_ID <<<"$result"
    export GUARDRAIL_TENANT_ID GUARDRAIL_EVENT_ID GUARDRAIL_EVENT_IDEMPOTENCY_KEY GUARDRAIL_ALLOCATION_ID GUARDRAIL_LEDGER_ID
}

cleanup_guardrail_fixture() {
    local database_url="$1"
    set +e
    if [[ -z "${GUARDRAIL_TENANT_ID:-}" ]]; then
        return
    fi
    psql "$database_url" -v ON_ERROR_STOP=1 >/dev/null <<SQL
BEGIN;
SET LOCAL app.current_tenant_id = '$GUARDRAIL_TENANT_ID';
ALTER TABLE attribution_recompute_jobs DISABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_allocations DISABLE TRIGGER trg_check_allocation_sum;
ALTER TABLE revenue_ledger DISABLE TRIGGER trg_ledger_prevent_mutation;
ALTER TABLE attribution_events DISABLE TRIGGER trg_events_prevent_mutation;
DELETE FROM attribution_recompute_jobs WHERE tenant_id = '$GUARDRAIL_TENANT_ID'::uuid;
DELETE FROM revenue_ledger WHERE tenant_id = '$GUARDRAIL_TENANT_ID'::uuid;
DELETE FROM attribution_allocations WHERE tenant_id = '$GUARDRAIL_TENANT_ID'::uuid;
DELETE FROM attribution_events WHERE tenant_id = '$GUARDRAIL_TENANT_ID'::uuid;
DELETE FROM tenants WHERE id = '$GUARDRAIL_TENANT_ID'::uuid;
ALTER TABLE attribution_recompute_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_allocations ENABLE TRIGGER trg_check_allocation_sum;
ALTER TABLE revenue_ledger ENABLE TRIGGER trg_ledger_prevent_mutation;
ALTER TABLE attribution_events ENABLE TRIGGER trg_events_prevent_mutation;
COMMIT;
SQL
    set -e
}
