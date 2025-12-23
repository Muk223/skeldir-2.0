"""
Schema contract guard to prevent drift between required columns and builder fixtures.

The guard:
- Introspects required columns (NOT NULL + no default, excluding identity)
- Ensures an approved builder exists for each core table
- Verifies the builder can create a valid row and required columns are non-null
"""

from __future__ import annotations

import asyncio
from typing import Dict, Iterable, List
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.tests.builders.manifest import CORE_TABLE_BUILDERS, TENANT_SCOPED_TABLES
from app.db.session import engine

REQUIRED_COLUMNS_QUERY = text(
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


async def _required_columns(table: str) -> List[str]:
    async with engine.begin() as conn:
        result = await conn.execute(REQUIRED_COLUMNS_QUERY, {"table_name": table})
    return sorted(result.scalars().all())


async def _fetch_required_values(table: str, row_id: UUID, tenant_id: UUID, columns: Iterable[str]) -> Dict[str, object]:
    select_cols = sorted(set(columns) | {"id"})
    async with engine.begin() as conn:
        if table in TENANT_SCOPED_TABLES and tenant_id:
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
        result = await conn.execute(
            text(
                f"SELECT {', '.join(select_cols)} FROM {table} WHERE id = :id"
            ),
            {"id": str(row_id)},
        )
        row = result.mappings().first()
    return dict(row or {})


@pytest.mark.asyncio
async def test_schema_contract_guard():
    failures: List[str] = []

    for table, builder in CORE_TABLE_BUILDERS.items():
        required_cols = await _required_columns(table)
        try:
            record = await builder()
            row_id = record.get("id")
            tenant_id = record.get("tenant_id") or row_id
        except IntegrityError as exc:
            failures.append(
                f"{table}: builder {builder.__name__} raised IntegrityError; required={required_cols}; error={exc}"
            )
            continue
        except Exception as exc:
            failures.append(
                f"{table}: builder {builder.__name__} failed ({exc}); required={required_cols}"
            )
            continue

        if not row_id:
            failures.append(f"{table}: builder {builder.__name__} did not return an id")
            continue

        row = await _fetch_required_values(table, row_id, tenant_id, required_cols)
        if not row:
            failures.append(
                f"{table}: builder {builder.__name__} inserted row id={row_id} but it was not found"
            )
            continue

        nulls = [col for col in required_cols if row.get(col) is None]
        if nulls:
            failures.append(
                f"{table}: builder {builder.__name__} produced NULL for required columns: {nulls}"
            )

    if failures:
        pytest.fail("Schema contract guard failures:\n" + "\n".join(failures))
