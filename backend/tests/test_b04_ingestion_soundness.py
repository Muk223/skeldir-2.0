"""
B0.4 ingestion soundness checks:
- Idempotency on attribution_events idempotency_key
- RLS isolation between tenants
- DLQ insertability (dead_events)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import engine


async def _required_columns(table: str):
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
          AND is_nullable = 'NO'
          AND column_default IS NULL
          AND (is_identity IS NULL OR is_identity = 'NO')
        """
    )
    async with engine.begin() as conn:
        result = await conn.execute(query, {"table_name": table})
    return set(result.scalars().all())


@pytest.mark.asyncio
async def test_idempotency_key_uniqueness():
    tenant_id = uuid4()
    idempotency_key = f"idem-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false)"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 ingestion soundness tenant seed
            text(
                """
                INSERT INTO tenants (id, name, api_key_hash, notification_email)
                VALUES (:id, :name, :api_key_hash, :email)
                """
            ),
            {
                "id": str(tenant_id),
                "name": "B04 Tenant",
                "api_key_hash": f"hash-{tenant_id.hex[:8]}",
                "email": f"{tenant_id.hex[:8]}@test.invalid",
            },
        )
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 ingestion soundness channel seed
            text(
                """
                INSERT INTO channel_taxonomy (code, display_name, family, is_paid)
                VALUES ('direct', 'direct', 'organic', false)
                ON CONFLICT (code) DO NOTHING
                """
            )
        )
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 ingestion soundness event insert
            text(
                """
                INSERT INTO attribution_events (tenant_id, session_id, idempotency_key, event_type, channel, event_timestamp, occurred_at, raw_payload)
                VALUES (:tenant_id, :session_id, :idem, 'click', 'direct', :ts, :ts, :payload)
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "session_id": str(uuid4()),
                "idem": idempotency_key,
                "ts": now,
                "payload": json.dumps({"source": "test"}),
            },
        )
        with pytest.raises(IntegrityError):
            await conn.execute(
                # RAW_SQL_ALLOWLIST: intentional duplicate insert to assert idempotency constraint
                text(
                    """
                    INSERT INTO attribution_events (tenant_id, session_id, idempotency_key, event_type, channel, event_timestamp, occurred_at, raw_payload)
                    VALUES (:tenant_id, :session_id, :idem, 'click', 'direct', :ts, :ts, :payload)
                    """
                ),
                {
                    "tenant_id": str(tenant_id),
                    "session_id": str(uuid4()),
                    "idem": idempotency_key,
                    "ts": now,
                    "payload": json.dumps({"source": "test"}),
                },
            )


@pytest.mark.asyncio
async def test_rls_isolation_between_tenants():
    tenant_a = uuid4()
    tenant_b = uuid4()
    async with engine.begin() as conn:
        for tid in (tenant_a, tenant_b):
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, false)"),
                {"tid": str(tid)},
            )
            await conn.execute(
                # RAW_SQL_ALLOWLIST: phase B0.4 RLS tenant seed
                text(
                    """
                    INSERT INTO tenants (id, name, api_key_hash, notification_email)
                    VALUES (:id, :name, :api_key_hash, :email)
                    """
                ),
                {
                    "id": str(tid),
                    "name": f"B04 {tid.hex[:4]}",
                    "api_key_hash": f"hash-{tid.hex[:8]}",
                    "email": f"{tid.hex[:8]}@test.invalid",
                },
            )
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 RLS channel seed
            text(
                """
                INSERT INTO channel_taxonomy (code, display_name, family, is_paid)
                VALUES ('direct', 'direct', 'organic', false)
                ON CONFLICT (code) DO NOTHING
                """
            )
        )
        await conn.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false)"),
            {"tid": str(tenant_a)},
        )
        event_id = uuid4()
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 RLS event insert
            text(
                """
                INSERT INTO attribution_events (id, tenant_id, session_id, idempotency_key, event_type, channel, event_timestamp, occurred_at, raw_payload)
                VALUES (:id, :tenant_id, :session_id, :idem, 'click', 'direct', :ts, :ts, :payload)
                """
            ),
            {
                "id": str(event_id),
                "tenant_id": str(tenant_a),
                "session_id": str(uuid4()),
                "idem": f"idem-{event_id.hex[:8]}",
                "ts": datetime.now(timezone.utc),
                "payload": json.dumps({"source": "test"}),
            },
        )
        await conn.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false)"),
            {"tid": str(tenant_b)},
        )
        result = await conn.execute(
            text("SELECT COUNT(*) FROM attribution_events WHERE id = :id"),
            {"id": str(event_id)},
        )
        visible = result.scalar_one()
        assert visible == 0, "Tenant B should not see Tenant A events under RLS"


@pytest.mark.asyncio
async def test_dead_events_insertable():
    tenant_id = uuid4()
    required = await _required_columns("dead_events")
    now = datetime.now(timezone.utc)
    payload = {
        "id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "ingested_at": now,
        "source": "webhook",
        "error_code": "INVALID_PAYLOAD",
        "error_detail": json.dumps({"reason": "malformed"}),
        "raw_payload": json.dumps({"bad": True}),
        "event_type": "webhook_failure",
        "error_type": "validation_error",
        "error_message": "invalid",
    }
    defaults = {
        "correlation_id": str(uuid4()),
        "external_event_id": "ext-1",
        "error_traceback": "",
        "retry_count": 0,
        "last_retry_at": now,
        "remediation_status": "pending",
        "remediation_notes": "",
        "resolved_at": now,
        "created_at": now,
        "updated_at": now,
    }
    for col in required:
        if col not in payload:
            payload[col] = defaults.get(col, "")
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(f":{k}" for k in payload.keys())
    async with engine.begin() as conn:
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 dead_events tenant seed
            text("INSERT INTO tenants (id, name, api_key_hash, notification_email) VALUES (:id, 'B04 DE', :hash, :email)"),
            {
                "id": str(tenant_id),
                "hash": f"hash-{tenant_id.hex[:8]}",
                "email": f"{tenant_id.hex[:8]}@test.invalid",
            },
        )
        await conn.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false)"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            # RAW_SQL_ALLOWLIST: phase B0.4 dead_events insert
            text(f"INSERT INTO dead_events ({columns}) VALUES ({placeholders})"),
            payload,
        )
        result = await conn.execute(
            text("SELECT COUNT(*) FROM dead_events WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        assert result.scalar_one() == 1, "dead_events insert should succeed for malformed payload"
