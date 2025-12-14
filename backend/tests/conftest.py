"""
Pytest fixtures for B0.4.3 tests.

Provides tenant creation/cleanup fixtures to satisfy FK constraints.
"""
import os
from uuid import uuid4

import pytest
from sqlalchemy import text

os.environ["TESTING"] = "1"

# B0.5.2: CI-first DSN unification
# Only set DATABASE_URL if not already provided by environment (e.g., CI, local override).
# CI must fail fast if Neon DSN leaks into test execution.
if "DATABASE_URL" not in os.environ:
    # Local dev default (should be overridden by .env or explicit export in production/CI)
    os.environ["DATABASE_URL"] = "postgresql://app_user:Sk3ld1r_App_Pr0d_2025!@ep-lucky-base-aedv3gwo-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# B0.5.2: CI guardrail - fail fast if Neon DSN detected in CI
if os.getenv("CI") == "true" and "neon.tech" in os.environ.get("DATABASE_URL", ""):
    raise RuntimeError(
        f"CI DSN MUST be localhost; resolved={os.environ['DATABASE_URL'].split('@')[1].split('/')[0]}"
    )

# B0.5.2: Diagnostic logging for CI DSN transparency
if os.getenv("CI") == "true":
    dsn = os.environ.get("DATABASE_URL", "NOT_SET")
    # Sanitize: show only host portion
    if "@" in dsn and "/" in dsn:
        host = dsn.split('@')[1].split('/')[0]
        print(f"[B0.5.2 DSN DIAGNOSTIC] Resolved DB host in CI: {host}")
    else:
        print(f"[B0.5.2 DSN DIAGNOSTIC] DATABASE_URL format unexpected: {dsn[:30]}...")

from app.db.session import engine


@pytest.fixture(scope="function")
async def test_tenant():
    """
    Create a test tenant record and clean up after test.

    Returns tenant_id UUID that satisfies FK constraints.
    """
    tenant_id = uuid4()
    api_key_hash = "test_hash_" + str(tenant_id)[:8]

    async with engine.begin() as conn:
        # Insert tenant record (id is the PK, not tenant_id)
        await conn.execute(
            text("""
                INSERT INTO tenants (id, api_key_hash, name, notification_email, created_at, updated_at)
                VALUES (:id, :api_key_hash, :name, :email, NOW(), NOW())
            """),
            {
                "id": str(tenant_id),
                "api_key_hash": api_key_hash,
                "name": f"Test Tenant {str(tenant_id)[:8]}",
                "email": f"test_{str(tenant_id)[:8]}@test.local",
            },
        )

    yield tenant_id

    # Cleanup - delete tenant and cascading records
    # Note: attribution_events is append-only (trg_events_prevent_mutation)
    # We cannot delete from it, so we skip cleanup for that table
    async with engine.begin() as conn:
        # Skip attribution_events cleanup (append-only)
        # await conn.execute(
        #     text("DELETE FROM attribution_events WHERE tenant_id = :tid"),
        #     {"tid": str(tenant_id)},
        # )

        # Dead events can be deleted (no mutation trigger)
        try:
            await conn.execute(
                text("DELETE FROM dead_events WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
        except Exception:
            pass  # Best effort cleanup

        # Tenants - may fail due to FK constraints from attribution_events
        # We'll leave test tenants in database for now
        # Production cleanup would use archival/retention policies
        # await conn.execute(
        #     text("DELETE FROM tenants WHERE id = :tid"),
        #     {"tid": str(tenant_id)},
        # )


@pytest.fixture(scope="function")
async def test_tenant_pair():
    """
    Create two test tenant records for RLS validation tests.

    Returns tuple (tenant_a_id, tenant_b_id).
    """
    tenant_a = uuid4()
    tenant_b = uuid4()

    async with engine.begin() as conn:
        # Insert both tenants
        for tenant_id in [tenant_a, tenant_b]:
            await conn.execute(
                text("""
                    INSERT INTO tenants (id, api_key_hash, name, notification_email, created_at, updated_at)
                    VALUES (:id, :api_key_hash, :name, :email, NOW(), NOW())
                """),
                {
                    "id": str(tenant_id),
                    "api_key_hash": f"test_hash_{str(tenant_id)[:8]}",
                    "name": f"Test Tenant {str(tenant_id)[:8]}",
                    "email": f"test_{str(tenant_id)[:8]}@test.local",
                },
            )

    yield (tenant_a, tenant_b)

    # Cleanup (best effort - attribution_events is append-only)
    async with engine.begin() as conn:
        for tenant_id in [tenant_a, tenant_b]:
            # Skip attribution_events (append-only)
            # Dead events cleanup
            try:
                await conn.execute(
                    text("DELETE FROM dead_events WHERE tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
            except Exception:
                pass
            # Skip tenants (FK constraints)
