from __future__ import annotations

import os
from typing import Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import psycopg2


def _normalize_psycopg_dsn(dsn: str) -> str:
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _safe_local_admin_dsn_from_runtime(runtime_dsn: str) -> str | None:
    """
    Best-effort derivation of a local Postgres superuser DSN from DATABASE_URL.

    This is intentionally conservative: it only derives an admin DSN for
    localhost-ish hosts (to avoid accidental writes to remote/prod DBs).
    """
    normalized = _normalize_psycopg_dsn(runtime_dsn)
    parsed = urlsplit(normalized)
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "db"}:
        return None

    # Keep db/host/port; swap creds to the canonical compose defaults.
    netloc = "postgres:postgres@" + host
    if parsed.port:
        netloc += f":{parsed.port}"
    rebuilt = urlunsplit(parsed._replace(netloc=netloc))
    return rebuilt


def admin_dsn() -> str | None:
    """
    Return a sync DSN usable by psycopg2 for privileged test seeding.

    Precedence:
    1) MIGRATION_DATABASE_URL (preferred, explicit)
    2) Derived from DATABASE_URL, but only for localhost/db
    """
    explicit = os.getenv("MIGRATION_DATABASE_URL", "").strip()
    if explicit:
        return _normalize_psycopg_dsn(explicit)

    runtime = os.getenv("DATABASE_URL", "").strip()
    if runtime:
        return _safe_local_admin_dsn_from_runtime(runtime)
    return None


def insert_tenant_admin(
    *,
    tenant_id: UUID,
    name: str,
    api_key_hash: str,
    columns: Iterable[str] | None = None,
    notification_email: str | None = None,
    secrets: Mapping[str, str] | None = None,
) -> None:
    dsn = admin_dsn()
    if not dsn:
        raise RuntimeError(
            "Tenant seeding requires a privileged DSN. Set MIGRATION_DATABASE_URL "
            "(preferred) or run against a local compose DB with DATABASE_URL on localhost."
        )

    conn = psycopg2.connect(dsn)
    insert_cols = ["id", "name"]
    params: dict[str, object] = {
        "id": str(tenant_id),
        "name": name,
        "api_key_hash": api_key_hash,
        "notification_email": notification_email or f"{str(tenant_id)[:8]}@test.invalid",
        "shopify_webhook_secret": (secrets or {}).get("shopify_webhook_secret"),
        "stripe_webhook_secret": (secrets or {}).get("stripe_webhook_secret"),
        "paypal_webhook_secret": (secrets or {}).get("paypal_webhook_secret"),
        "woocommerce_webhook_secret": (secrets or {}).get("woocommerce_webhook_secret"),
    }

    try:
        conn.autocommit = True
        cur = conn.cursor()

        if columns is None:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='tenants'
                """
            )
            available = {row[0] for row in cur.fetchall()}
        else:
            available = set(columns)

        if "api_key_hash" in available:
            insert_cols.append("api_key_hash")
        if "notification_email" in available:
            insert_cols.append("notification_email")

        for secret_col in (
            "shopify_webhook_secret",
            "stripe_webhook_secret",
            "paypal_webhook_secret",
            "woocommerce_webhook_secret",
        ):
            if secret_col in available and params.get(secret_col) is not None:
                insert_cols.append(secret_col)

        values_clause = ", ".join(f"%({col})s" for col in insert_cols)
        sql = f"INSERT INTO public.tenants ({', '.join(insert_cols)}) VALUES ({values_clause})"
        cur.execute(sql, params)
    finally:
        conn.close()
