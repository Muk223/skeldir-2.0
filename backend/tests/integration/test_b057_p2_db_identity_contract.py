from __future__ import annotations

import os
from uuid import UUID, uuid4

import psycopg2
import pytest


def _psycopg_dsn_from_env(var_name: str) -> str:
    value = os.getenv(var_name, "").strip()
    if not value:
        raise RuntimeError(f"{var_name} must be set for integration tests")
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def _admin_conn():
    dsn = _psycopg_dsn_from_env("MIGRATION_DATABASE_URL")
    return psycopg2.connect(dsn)


def _runtime_conn():
    dsn = _psycopg_dsn_from_env("DATABASE_URL")
    return psycopg2.connect(dsn)


def _tenant_columns(cur) -> set[str]:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='tenants'")
    return {row[0] for row in cur.fetchall()}


def _seed_tenant(*, tenant_id: UUID, api_key_hash: str) -> None:
    conn = _admin_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        columns = _tenant_columns(cur)

        insert_cols = ["id", "name"]
        params = {
            "id": str(tenant_id),
            "name": f"Test Tenant {str(tenant_id)[:8]}",
            "api_key_hash": api_key_hash,
            "notification_email": f"test_{str(tenant_id)[:8]}@test.local",
            "shopify_webhook_secret": "test_shopify_secret",
            "stripe_webhook_secret": "test_stripe_secret",
            "paypal_webhook_secret": "test_paypal_secret",
            "woocommerce_webhook_secret": "test_woocommerce_secret",
        }

        for optional_col in (
            "api_key_hash",
            "notification_email",
            "shopify_webhook_secret",
            "stripe_webhook_secret",
            "paypal_webhook_secret",
            "woocommerce_webhook_secret",
        ):
            if optional_col in columns:
                insert_cols.append(optional_col)

        values_clause = ", ".join(f"%({col})s" for col in insert_cols)
        cur.execute(
            f"INSERT INTO public.tenants ({', '.join(insert_cols)}) VALUES ({values_clause})",
            params,
        )
    finally:
        conn.close()


@pytest.mark.integration
def test_p2_runtime_cannot_select_tenants_directly():
    conn = _runtime_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        with pytest.raises(psycopg2.Error) as excinfo:
            cur.execute("SELECT id FROM public.tenants LIMIT 1")
        assert "permission denied for table tenants" in str(excinfo.value)
    finally:
        conn.close()


@pytest.mark.integration
def test_p2_runtime_can_execute_tenant_resolution_interfaces():
    tenant_id = uuid4()
    api_key_hash = f"test_hash_{str(tenant_id)[:8]}"
    _seed_tenant(tenant_id=tenant_id, api_key_hash=api_key_hash)

    conn = _runtime_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT tenant_id FROM security.list_tenant_ids()")
        tenant_ids = {UUID(str(row[0])) for row in cur.fetchall()}
        assert tenant_id in tenant_ids

        cur.execute("SELECT * FROM security.resolve_tenant_webhook_secrets(%s)", (api_key_hash,))
        row = cur.fetchone()
        assert row is not None

        column_names = [col.name for col in cur.description]
        assert set(column_names) == {
            "tenant_id",
            "shopify_webhook_secret",
            "stripe_webhook_secret",
            "paypal_webhook_secret",
            "woocommerce_webhook_secret",
        }
        assert UUID(str(row[column_names.index("tenant_id")])) == tenant_id
    finally:
        conn.close()


@pytest.mark.integration
def test_p2_llm_api_calls_insert_is_fail_closed_without_tenant_context():
    tenant_id = uuid4()
    api_key_hash = f"test_hash_{str(tenant_id)[:8]}"
    _seed_tenant(tenant_id=tenant_id, api_key_hash=api_key_hash)

    conn = _runtime_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(
            "SELECT has_table_privilege(current_user, 'public.llm_api_calls', 'INSERT')"
        )
        assert cur.fetchone()[0] is True

        request_id = f"p2-test-{uuid4()}"
        with pytest.raises(psycopg2.Error) as excinfo:
            cur.execute(
                """
                INSERT INTO public.llm_api_calls (
                    tenant_id,
                    endpoint,
                    request_id,
                    model,
                    input_tokens,
                    output_tokens,
                    cost_cents,
                    latency_ms,
                    was_cached,
                    request_metadata
                ) VALUES (
                    %(tenant_id)s,
                    'p2.test',
                    %(request_id)s,
                    'stub',
                    0,
                    0,
                    0,
                    0,
                    false,
                    '{}'::jsonb
                )
                """,
                {"tenant_id": str(tenant_id), "request_id": request_id},
            )
        assert "row-level security" in str(excinfo.value).lower()

        cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cur.execute(
            """
            INSERT INTO public.llm_api_calls (
                tenant_id,
                endpoint,
                request_id,
                model,
                input_tokens,
                output_tokens,
                cost_cents,
                latency_ms,
                was_cached,
                request_metadata
            ) VALUES (
                %(tenant_id)s,
                'p2.test',
                %(request_id)s,
                'stub',
                0,
                0,
                0,
                0,
                false,
                '{}'::jsonb
            )
            """,
            {"tenant_id": str(tenant_id), "request_id": request_id + "-ok"},
        )
    finally:
        conn.close()

