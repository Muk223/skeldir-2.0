"""
R3 — Ingestion Under Fire (Idempotency + DLQ + PII)

Adversarial harness that drives real HTTP webhook ingestion endpoints and then
cross-checks truth in Postgres (canonical tables + DLQ) with deterministic seeds.

This script is intentionally browser-verifiable via stdout: it prints scenario
verdict blocks and post-run DB truth queries (counts + duplicates + PII scans).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import asyncpg
import httpx


PII_KEYS = [
    "email",
    "email_address",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "ip",
    "ip_address",
    "first_name",
    "last_name",
    "full_name",
    "address",
    "street_address",
    "billing_address",
    "shipping_address",
    "receipt_email",
    "customer_email",
    "customer_phone",
]


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        if default is None:
            raise RuntimeError(f"Missing required env var: {name}")
        return default
    return value


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _uuid_deterministic(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, ":".join(parts))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def sign_stripe(body: bytes, secret: str) -> str:
    ts = int(_now_utc().timestamp())
    signed_payload = f"{ts}.{body.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


@dataclass(frozen=True)
class TenantSeed:
    tenant_id: UUID
    api_key: str
    api_key_hash: str
    secrets: dict[str, str]


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    passed: bool
    http_status_counts: dict[str, int]
    http_timeouts: int
    http_connection_errors: int
    db: dict[str, Any]


async def _pg_connect(database_url: str) -> asyncpg.Connection:
    return await asyncpg.connect(database_url)


async def _set_tenant_context(conn: asyncpg.Connection, tenant_id: UUID) -> None:
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)",
        str(tenant_id),
    )


async def seed_tenant(conn: asyncpg.Connection, seed: TenantSeed) -> None:
    await conn.execute(
        """
        INSERT INTO tenants (
          id, api_key_hash, name, notification_email,
          shopify_webhook_secret, stripe_webhook_secret,
          paypal_webhook_secret, woocommerce_webhook_secret,
          created_at, updated_at
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW(),NOW())
        ON CONFLICT (id) DO NOTHING
        """,
        str(seed.tenant_id),
        seed.api_key_hash,
        f"R3 Tenant {str(seed.tenant_id)[:8]}",
        f"r3_{str(seed.tenant_id)[:8]}@test.invalid",
        seed.secrets["shopify"],
        seed.secrets["stripe"],
        seed.secrets["paypal"],
        seed.secrets["woocommerce"],
    )


async def seed_channel_taxonomy(conn: asyncpg.Connection) -> None:
    # Must match backend/app/ingestion/channel_normalization.get_valid_taxonomy_codes()
    rows = [
        ("unknown", "unknown", False, "Unknown"),
        ("direct", "direct", False, "Direct"),
        ("email", "email", False, "Email"),
        ("facebook_brand", "paid_social", True, "Facebook Brand"),
        ("facebook_paid", "paid_social", True, "Facebook Paid"),
        ("google_display_paid", "paid_search", True, "Google Display Paid"),
        ("google_search_paid", "paid_search", True, "Google Search Paid"),
        ("organic", "organic", False, "Organic"),
        ("referral", "referral", False, "Referral"),
        ("tiktok_paid", "paid_social", True, "TikTok Paid"),
    ]
    for code, family, is_paid, display_name in rows:
        await conn.execute(
            """
            INSERT INTO channel_taxonomy (code, family, is_paid, display_name, is_active, state, created_at)
            VALUES ($1,$2,$3,$4,TRUE,'active',NOW())
            ON CONFLICT (code) DO NOTHING
            """,
            code,
            family,
            is_paid,
            display_name,
        )


async def _http_fire(
    client: httpx.AsyncClient,
    requests: list[tuple[str, dict[str, str], bytes]],
    concurrency: int,
    timeout_s: float,
) -> tuple[dict[str, int], int, int]:
    sem = asyncio.Semaphore(concurrency)
    status_counts: dict[str, int] = {}
    timeouts = 0
    connection_errors = 0

    async def _one(url: str, headers: dict[str, str], body: bytes) -> None:
        nonlocal timeouts, connection_errors
        async with sem:
            try:
                resp = await client.post(url, content=body, headers=headers, timeout=timeout_s)
                key = str(resp.status_code)
                status_counts[key] = status_counts.get(key, 0) + 1
            except (httpx.TimeoutException, asyncio.TimeoutError):
                timeouts += 1
                status_counts["timeout"] = status_counts.get("timeout", 0) + 1
            except httpx.RequestError:
                connection_errors += 1
                status_counts["request_error"] = status_counts.get("request_error", 0) + 1

    await asyncio.gather(*[_one(url, headers, body) for (url, headers, body) in requests])
    return status_counts, timeouts, connection_errors


def _verdict_block(name: str, payload: dict[str, Any]) -> None:
    print(f"R3_VERDICT_BEGIN {name}")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"R3_VERDICT_END {name}")


def _parse_int_list(csv: str) -> list[int]:
    out: list[int] = []
    for part in [p.strip() for p in csv.split(",") if p.strip()]:
        out.append(int(part))
    return out


async def db_count_canonical_for_key(conn: asyncpg.Connection, tenant_id: UUID, key: str) -> int:
    await _set_tenant_context(conn, tenant_id)
    return int(
        await conn.fetchval(
            "SELECT COUNT(*) FROM attribution_events WHERE tenant_id=$1 AND idempotency_key=$2",
            str(tenant_id),
            key,
        )
    )


async def db_count_dlq_for_key(conn: asyncpg.Connection, tenant_id: UUID, key: str) -> int:
    await _set_tenant_context(conn, tenant_id)
    return int(
        await conn.fetchval(
            "SELECT COUNT(*) FROM dead_events WHERE tenant_id=$1 AND raw_payload->>'idempotency_key'=$2",
            str(tenant_id),
            key,
        )
    )


async def db_count_canonical_for_keys(
    conn: asyncpg.Connection, tenant_id: UUID, keys: list[str]
) -> int:
    if not keys:
        return 0
    await _set_tenant_context(conn, tenant_id)
    return int(
        await conn.fetchval(
            "SELECT COUNT(*) FROM attribution_events WHERE tenant_id=$1 AND idempotency_key = ANY($2::text[])",
            str(tenant_id),
            keys,
        )
    )


async def db_count_dlq_for_keys(conn: asyncpg.Connection, tenant_id: UUID, keys: list[str]) -> int:
    if not keys:
        return 0
    await _set_tenant_context(conn, tenant_id)
    return int(
        await conn.fetchval(
            "SELECT COUNT(*) FROM dead_events WHERE tenant_id=$1 AND raw_payload->>'idempotency_key' = ANY($2::text[])",
            str(tenant_id),
            keys,
        )
    )


async def db_pii_key_hits_since(
    conn: asyncpg.Connection, since_utc: datetime, tenant_ids: list[UUID]
) -> dict[str, int]:
    clauses = " OR ".join([f"jsonb_path_exists(raw_payload, '$.**.{k}')" for k in PII_KEYS])
    canonical_hits = 0
    dlq_hits = 0
    for tenant_id in tenant_ids:
        await _set_tenant_context(conn, tenant_id)
        canonical_hits += int(
            await conn.fetchval(
                f"""
                SELECT COUNT(*) FROM attribution_events
                WHERE created_at >= $1 AND tenant_id = $2 AND ({clauses})
                """,
                since_utc,
                str(tenant_id),
            )
        )
        dlq_hits += int(
            await conn.fetchval(
                f"""
                SELECT COUNT(*) FROM dead_events
                WHERE ingested_at >= $1 AND tenant_id = $2 AND ({clauses})
                """,
                since_utc,
                str(tenant_id),
            )
        )
    return {
        "attribution_events_raw_payload_hits": canonical_hits,
        "dead_events_raw_payload_hits": dlq_hits,
    }


def build_stripe_payment_intent_body(
    *,
    event_id: str,
    payment_intent_id: str | None,
    amount_cents: int | None,
    currency: str | None,
    created_epoch: Any,
    include_pii: bool,
) -> bytes:
    body: dict[str, Any] = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "created": created_epoch,
        "data": {
            "object": {
                "id": payment_intent_id,
                "amount": amount_cents,
                "currency": currency,
                "status": "succeeded",
            }
        },
    }
    if include_pii:
        body["email"] = "pii_user@test.invalid"
        body["ip_address"] = "203.0.113.99"
        body["data"]["object"]["receipt_email"] = "receipt@test.invalid"
        body["data"]["object"]["billing_details"] = {"email": "bill@test.invalid", "name": "Test User"}
    return json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _make_headers_for_stripe(
    *,
    tenant_api_key_header: str,
    tenant_api_key: str,
    stripe_secret: str,
    correlation_id: UUID,
    idempotency_key: str,
    body: bytes,
) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Correlation-ID": str(correlation_id),
        tenant_api_key_header: tenant_api_key,
        "X-Idempotency-Key": idempotency_key,
        "Stripe-Signature": sign_stripe(body, stripe_secret),
    }


def _keys_for_scenario(candidate_sha: str, scenario: str, n: int) -> list[str]:
    return [str(_uuid_deterministic("r3", candidate_sha, scenario, str(i))) for i in range(n)]


async def scenario_s1_replay_storm(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant: TenantSeed,
    tenant_api_key_header: str,
    n: int,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    idempotency_key: str,
) -> ScenarioResult:
    correlation_id = _uuid_deterministic("r3", name, str(tenant.tenant_id), idempotency_key)
    body = build_stripe_payment_intent_body(
        event_id=f"evt_{idempotency_key.replace('-', '')[:16]}",
        payment_intent_id=f"pi_{idempotency_key.replace('-', '')[:16]}",
        amount_cents=19999,
        currency="usd",
        created_epoch=int(run_start_utc.timestamp()),
        include_pii=False,
    )
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    headers = _make_headers_for_stripe(
        tenant_api_key_header=tenant_api_key_header,
        tenant_api_key=tenant.api_key,
        stripe_secret=tenant.secrets["stripe"],
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        body=body,
    )
    reqs = [(url, headers, body) for _ in range(n)]
    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )

    canonical = await db_count_canonical_for_key(conn, tenant.tenant_id, idempotency_key)
    dlq = await db_count_dlq_for_key(conn, tenant.tenant_id, idempotency_key)
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    passed = canonical == 1 and dlq == 0 and http_5xx == 0 and timeouts == 0 and conn_errors == 0
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "CANONICAL_ROWS_FOR_KEY": canonical,
            "DLQ_ROWS_FOR_KEY": dlq,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def scenario_s2_unique_storm(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant: TenantSeed,
    tenant_api_key_header: str,
    n: int,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    keys: list[str],
) -> ScenarioResult:
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    reqs: list[tuple[str, dict[str, str], bytes]] = []
    for k in keys:
        correlation_id = _uuid_deterministic("r3", name, str(tenant.tenant_id), k)
        body = build_stripe_payment_intent_body(
            event_id=f"evt_{k.replace('-', '')[:16]}",
            payment_intent_id=f"pi_{k.replace('-', '')[:16]}",
            amount_cents=100,
            currency="usd",
            created_epoch=int(run_start_utc.timestamp()),
            include_pii=False,
        )
        headers = _make_headers_for_stripe(
            tenant_api_key_header=tenant_api_key_header,
            tenant_api_key=tenant.api_key,
            stripe_secret=tenant.secrets["stripe"],
            correlation_id=correlation_id,
            idempotency_key=k,
            body=body,
        )
        reqs.append((url, headers, body))

    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )
    canonical = await db_count_canonical_for_keys(conn, tenant.tenant_id, keys)
    dlq = await db_count_dlq_for_keys(conn, tenant.tenant_id, keys)
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    passed = canonical == n and dlq == 0 and http_5xx == 0 and timeouts == 0 and conn_errors == 0
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "CANONICAL_ROWS_CREATED": canonical,
            "DLQ_ROWS_CREATED": dlq,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def scenario_s3_malformed_storm(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant: TenantSeed,
    tenant_api_key_header: str,
    n: int,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    keys: list[str],
) -> ScenarioResult:
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    reqs: list[tuple[str, dict[str, str], bytes]] = []
    for k in keys:
        correlation_id = _uuid_deterministic("r3", name, str(tenant.tenant_id), k)
        body = build_stripe_payment_intent_body(
            event_id=f"evt_{k.replace('-', '')[:16]}",
            payment_intent_id=None,
            amount_cents=None,
            currency="usd",
            created_epoch="not_an_int",
            include_pii=False,
        )
        headers = _make_headers_for_stripe(
            tenant_api_key_header=tenant_api_key_header,
            tenant_api_key=tenant.api_key,
            stripe_secret=tenant.secrets["stripe"],
            correlation_id=correlation_id,
            idempotency_key=k,
            body=body,
        )
        reqs.append((url, headers, body))

    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )
    canonical = await db_count_canonical_for_keys(conn, tenant.tenant_id, keys)
    dlq = await db_count_dlq_for_keys(conn, tenant.tenant_id, keys)
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    passed = canonical == 0 and dlq == n and http_5xx == 0 and timeouts == 0 and conn_errors == 0
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "CANONICAL_ROWS_CREATED": canonical,
            "DLQ_ROWS_CREATED": dlq,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def scenario_s4_pii_storm(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant: TenantSeed,
    tenant_api_key_header: str,
    n: int,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    keys: list[str],
) -> ScenarioResult:
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    reqs: list[tuple[str, dict[str, str], bytes]] = []
    for k in keys:
        correlation_id = _uuid_deterministic("r3", name, str(tenant.tenant_id), k)
        body = build_stripe_payment_intent_body(
            event_id=f"evt_{k.replace('-', '')[:16]}",
            payment_intent_id=f"pi_{k.replace('-', '')[:16]}",
            amount_cents=321,
            currency="usd",
            created_epoch=int(run_start_utc.timestamp()),
            include_pii=True,
        )
        headers = _make_headers_for_stripe(
            tenant_api_key_header=tenant_api_key_header,
            tenant_api_key=tenant.api_key,
            stripe_secret=tenant.secrets["stripe"],
            correlation_id=correlation_id,
            idempotency_key=k,
            body=body,
        )
        reqs.append((url, headers, body))

    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )
    canonical = await db_count_canonical_for_keys(conn, tenant.tenant_id, keys)
    dlq = await db_count_dlq_for_keys(conn, tenant.tenant_id, keys)
    pii_hits = await db_pii_key_hits_since(conn, run_start_utc, [tenant.tenant_id])
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    passed = (
        canonical == 0
        and dlq == n
        and http_5xx == 0
        and timeouts == 0
        and conn_errors == 0
        and sum(pii_hits.values()) == 0
    )
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "CANONICAL_ROWS_CREATED": canonical,
            "DLQ_ROWS_CREATED": dlq,
            "PII_KEY_HIT_COUNT_IN_DB": sum(pii_hits.values()),
            **pii_hits,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def scenario_s5_cross_tenant_collision(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant_a: TenantSeed,
    tenant_b: TenantSeed,
    tenant_api_key_header: str,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    idempotency_key: str,
) -> ScenarioResult:
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    body = build_stripe_payment_intent_body(
        event_id=f"evt_{idempotency_key.replace('-', '')[:16]}",
        payment_intent_id=f"pi_{idempotency_key.replace('-', '')[:16]}",
        amount_cents=777,
        currency="usd",
        created_epoch=int(run_start_utc.timestamp()),
        include_pii=False,
    )
    headers_a = _make_headers_for_stripe(
        tenant_api_key_header=tenant_api_key_header,
        tenant_api_key=tenant_a.api_key,
        stripe_secret=tenant_a.secrets["stripe"],
        correlation_id=_uuid_deterministic("r3", name, "A", idempotency_key),
        idempotency_key=idempotency_key,
        body=body,
    )
    headers_b = _make_headers_for_stripe(
        tenant_api_key_header=tenant_api_key_header,
        tenant_api_key=tenant_b.api_key,
        stripe_secret=tenant_b.secrets["stripe"],
        correlation_id=_uuid_deterministic("r3", name, "B", idempotency_key),
        idempotency_key=idempotency_key,
        body=body,
    )
    reqs = [(url, headers_a, body), (url, headers_b, body)]
    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )

    a_canonical = await db_count_canonical_for_key(conn, tenant_a.tenant_id, idempotency_key)
    b_canonical = await db_count_canonical_for_key(conn, tenant_b.tenant_id, idempotency_key)
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    passed = (
        a_canonical == 1
        and b_canonical == 1
        and http_5xx == 0
        and timeouts == 0
        and conn_errors == 0
    )
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "TENANT_A_CANONICAL_ROWS_FOR_KEY": a_canonical,
            "TENANT_B_CANONICAL_ROWS_FOR_KEY": b_canonical,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def scenario_s6_mixed_storm(
    *,
    name: str,
    client: httpx.AsyncClient,
    base_url: str,
    tenant: TenantSeed,
    tenant_api_key_header: str,
    n: int,
    concurrency: int,
    timeout_s: float,
    run_start_utc: datetime,
    conn: asyncpg.Connection,
    replay_key: str,
    unique_keys: list[str],
    malformed_keys: list[str],
) -> ScenarioResult:
    url = f"{base_url}/api/webhooks/stripe/payment_intent/succeeded"
    reqs: list[tuple[str, dict[str, str], bytes]] = []

    replay_body = build_stripe_payment_intent_body(
        event_id=f"evt_{replay_key.replace('-', '')[:16]}",
        payment_intent_id=f"pi_{replay_key.replace('-', '')[:16]}",
        amount_cents=123,
        currency="usd",
        created_epoch=int(run_start_utc.timestamp()),
        include_pii=False,
    )
    replay_headers = _make_headers_for_stripe(
        tenant_api_key_header=tenant_api_key_header,
        tenant_api_key=tenant.api_key,
        stripe_secret=tenant.secrets["stripe"],
        correlation_id=_uuid_deterministic("r3", name, str(tenant.tenant_id), replay_key),
        idempotency_key=replay_key,
        body=replay_body,
    )
    # MixedStorm shape: 70% replay duplicates + 30% unique + 10% malformed (intentional overlap).
    for _ in range(max(1, int(0.7 * n))):
        reqs.append((url, replay_headers, replay_body))

    for k in unique_keys:
        body = build_stripe_payment_intent_body(
            event_id=f"evt_{k.replace('-', '')[:16]}",
            payment_intent_id=f"pi_{k.replace('-', '')[:16]}",
            amount_cents=222,
            currency="usd",
            created_epoch=int(run_start_utc.timestamp()),
            include_pii=False,
        )
        headers = _make_headers_for_stripe(
            tenant_api_key_header=tenant_api_key_header,
            tenant_api_key=tenant.api_key,
            stripe_secret=tenant.secrets["stripe"],
            correlation_id=_uuid_deterministic("r3", name, str(tenant.tenant_id), k),
            idempotency_key=k,
            body=body,
        )
        reqs.append((url, headers, body))

    for k in malformed_keys:
        body = build_stripe_payment_intent_body(
            event_id=f"evt_{k.replace('-', '')[:16]}",
            payment_intent_id=None,
            amount_cents=None,
            currency="usd",
            created_epoch="not_an_int",
            include_pii=False,
        )
        headers = _make_headers_for_stripe(
            tenant_api_key_header=tenant_api_key_header,
            tenant_api_key=tenant.api_key,
            stripe_secret=tenant.secrets["stripe"],
            correlation_id=_uuid_deterministic("r3", name, str(tenant.tenant_id), k),
            idempotency_key=k,
            body=body,
        )
        reqs.append((url, headers, body))

    reqs.sort(key=lambda r: hashlib.sha256(r[1]["X-Idempotency-Key"].encode("utf-8")).hexdigest())

    status_counts, timeouts, conn_errors = await _http_fire(
        client, reqs, concurrency=concurrency, timeout_s=timeout_s
    )
    http_5xx = sum(v for k, v in status_counts.items() if k.isdigit() and 500 <= int(k) <= 599)

    replay_canonical = await db_count_canonical_for_key(conn, tenant.tenant_id, replay_key)
    unique_canonical = await db_count_canonical_for_keys(conn, tenant.tenant_id, unique_keys)
    malformed_dlq = await db_count_dlq_for_keys(conn, tenant.tenant_id, malformed_keys)

    passed = (
        replay_canonical == 1
        and unique_canonical == len(unique_keys)
        and malformed_dlq == len(malformed_keys)
        and http_5xx == 0
        and timeouts == 0
        and conn_errors == 0
    )
    return ScenarioResult(
        name=name,
        passed=passed,
        http_status_counts=status_counts,
        http_timeouts=timeouts,
        http_connection_errors=conn_errors,
        db={
            "REPLAY_CANONICAL_ROWS_FOR_KEY": replay_canonical,
            "UNIQUE_CANONICAL_ROWS_CREATED": unique_canonical,
            "MALFORMED_DLQ_ROWS_CREATED": malformed_dlq,
            "HTTP_5XX_COUNT": http_5xx,
            "HTTP_TIMEOUT_COUNT": timeouts,
            "HTTP_CONNECTION_ERRORS": conn_errors,
        },
    )


async def main() -> int:
    candidate_sha = os.getenv("CANDIDATE_SHA") or os.getenv("GITHUB_SHA") or _env("CANDIDATE_SHA", default="local")
    base_url = _env("R3_API_BASE_URL", default="http://127.0.0.1:8000")
    db_url = _env("R3_DATABASE_URL", default=_env("DATABASE_URL", default=""))
    tenant_api_key_header = _env("TENANT_API_KEY_HEADER", default="X-Skeldir-Tenant-Key")

    ladder = _parse_int_list(_env("R3_LADDER", default="50,250,1000"))
    concurrency = int(_env("R3_CONCURRENCY", default="200"))
    timeout_s = float(_env("R3_TIMEOUT_S", default="10"))
    run_start_utc = _now_utc()

    print("=== R3_ENV ===")
    print(
        json.dumps(
            {
                "candidate_sha": candidate_sha,
                "run_start_utc": run_start_utc.isoformat(),
                "base_url": base_url,
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "concurrency": concurrency,
                "timeout_s": timeout_s,
                "ladder": ladder,
            },
            indent=2,
            sort_keys=True,
        )
    )

    tenant_a_id = _uuid_deterministic("r3", candidate_sha, "tenant", "A")
    tenant_b_id = _uuid_deterministic("r3", candidate_sha, "tenant", "B")
    tenant_a_api_key = f"r3_{candidate_sha[:12]}_A_{tenant_a_id}"
    tenant_b_api_key = f"r3_{candidate_sha[:12]}_B_{tenant_b_id}"

    tenant_a = TenantSeed(
        tenant_id=tenant_a_id,
        api_key=tenant_a_api_key,
        api_key_hash=_sha256_hex(tenant_a_api_key),
        secrets={
            "shopify": f"r3_shopify_{candidate_sha[:12]}_A",
            "stripe": f"r3_stripe_{candidate_sha[:12]}_A",
            "paypal": f"r3_paypal_{candidate_sha[:12]}_A",
            "woocommerce": f"r3_woo_{candidate_sha[:12]}_A",
        },
    )
    tenant_b = TenantSeed(
        tenant_id=tenant_b_id,
        api_key=tenant_b_api_key,
        api_key_hash=_sha256_hex(tenant_b_api_key),
        secrets={
            "shopify": f"r3_shopify_{candidate_sha[:12]}_B",
            "stripe": f"r3_stripe_{candidate_sha[:12]}_B",
            "paypal": f"r3_paypal_{candidate_sha[:12]}_B",
            "woocommerce": f"r3_woo_{candidate_sha[:12]}_B",
        },
    )

    print("=== EG-R3-0 (Truth Anchor & Clean Room) ===")
    print(f"CANDIDATE_SHA={candidate_sha}")
    print(f"TENANT_A_ID={tenant_a.tenant_id}")
    print(f"TENANT_B_ID={tenant_b.tenant_id}")

    conn = await _pg_connect(db_url)
    try:
        await seed_channel_taxonomy(conn)
        await seed_tenant(conn, tenant_a)
        await seed_tenant(conn, tenant_b)
    finally:
        await conn.close()

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits) as client:
        conn2 = await _pg_connect(db_url)
        try:
            all_results: list[ScenarioResult] = []

            for n in ladder:
                print(f"=== R3_LADDER_STEP N={n} ===")

                s1_key = str(_uuid_deterministic("r3", candidate_sha, "S1", "replay_key"))
                s1 = await scenario_s1_replay_storm(
                    name=f"S1_ReplayStorm_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant=tenant_a,
                    tenant_api_key_header=tenant_api_key_header,
                    n=n,
                    concurrency=concurrency,
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    idempotency_key=s1_key,
                )
                _verdict_block(s1.name, {"passed": s1.passed, **s1.db, "http_status_counts": s1.http_status_counts})
                all_results.append(s1)
                if not s1.passed:
                    break

                s5_key = str(_uuid_deterministic("r3", candidate_sha, "S5", "collision_key"))
                s5 = await scenario_s5_cross_tenant_collision(
                    name=f"S5_CrossTenantCollision_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant_a=tenant_a,
                    tenant_b=tenant_b,
                    tenant_api_key_header=tenant_api_key_header,
                    concurrency=min(concurrency, 50),
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    idempotency_key=s5_key,
                )
                _verdict_block(s5.name, {"passed": s5.passed, **s5.db, "http_status_counts": s5.http_status_counts})
                all_results.append(s5)
                if not s5.passed:
                    break

                s3_keys = _keys_for_scenario(candidate_sha, f"S3_{n}", n)
                s3 = await scenario_s3_malformed_storm(
                    name=f"S3_MalformedStorm_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant=tenant_a,
                    tenant_api_key_header=tenant_api_key_header,
                    n=n,
                    concurrency=min(concurrency, 100),
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    keys=s3_keys,
                )
                _verdict_block(s3.name, {"passed": s3.passed, **s3.db, "http_status_counts": s3.http_status_counts})
                all_results.append(s3)
                if not s3.passed:
                    break

                s4_keys = _keys_for_scenario(candidate_sha, f"S4_{n}", n)
                s4 = await scenario_s4_pii_storm(
                    name=f"S4_PIIStorm_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant=tenant_a,
                    tenant_api_key_header=tenant_api_key_header,
                    n=n,
                    concurrency=min(concurrency, 100),
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    keys=s4_keys,
                )
                _verdict_block(s4.name, {"passed": s4.passed, **s4.db, "http_status_counts": s4.http_status_counts})
                all_results.append(s4)
                if not s4.passed:
                    break

                s2_keys = _keys_for_scenario(candidate_sha, f"S2_{n}", n)
                s2 = await scenario_s2_unique_storm(
                    name=f"S2_UniqueStorm_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant=tenant_a,
                    tenant_api_key_header=tenant_api_key_header,
                    n=n,
                    concurrency=min(concurrency, 100),
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    keys=s2_keys,
                )
                _verdict_block(s2.name, {"passed": s2.passed, **s2.db, "http_status_counts": s2.http_status_counts})
                all_results.append(s2)
                if not s2.passed:
                    break

                replay_key = str(_uuid_deterministic("r3", candidate_sha, f"S6_{n}", "replay"))
                unique_keys = _keys_for_scenario(candidate_sha, f"S6_{n}_unique", max(1, int(0.3 * n)))
                malformed_keys = _keys_for_scenario(candidate_sha, f"S6_{n}_malformed", max(1, int(0.1 * n)))
                s6 = await scenario_s6_mixed_storm(
                    name=f"S6_MixedStorm_N{n}",
                    client=client,
                    base_url=base_url,
                    tenant=tenant_a,
                    tenant_api_key_header=tenant_api_key_header,
                    n=n,
                    concurrency=concurrency,
                    timeout_s=timeout_s,
                    run_start_utc=run_start_utc,
                    conn=conn2,
                    replay_key=replay_key,
                    unique_keys=unique_keys,
                    malformed_keys=malformed_keys,
                )
                _verdict_block(s6.name, {"passed": s6.passed, **s6.db, "http_status_counts": s6.http_status_counts})
                all_results.append(s6)
                if not s6.passed:
                    break

            all_passed = all(r.passed for r in all_results)
            print("=== EG-R3-6 (Evidence Pack) ===")
            print(f"SCENARIOS_EXECUTED={len(all_results)}")
            print(f"ALL_SCENARIOS_PASSED={all_passed}")

            return 0 if all_passed else 1
        finally:
            await conn2.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
