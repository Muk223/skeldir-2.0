#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import psycopg2
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ContractTarget(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: str = Field(alias="schema")
    table: str
    tenant_scoped: bool = True


class RequiredColumn(BaseModel):
    name: str
    type: str
    nullable: bool
    constraints: list[str] = Field(default_factory=list)
    notes: str | None = None


class RowShape(BaseModel):
    required_columns: list[RequiredColumn]
    required_uniques: list[list[str]]


class LLMWriteContract(BaseModel):
    contract_id: str
    contract_version: str
    owner: Literal["llm"]
    purpose: str
    targets: list[ContractTarget]
    current_row_shape: RowShape
    target_row_shape: RowShape

    @field_validator("targets")
    @classmethod
    def _targets_non_empty(cls, value: list[ContractTarget]) -> list[ContractTarget]:
        if not value:
            raise ValueError("targets must not be empty")
        return value


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    name: str
    db_type: str
    nullable: bool


@dataclass(frozen=True, slots=True)
class SchemaSnapshot:
    schema: str
    table: str
    columns: list[ColumnInfo]
    uniques: list[list[str]]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_contract_type(raw: str) -> str:
    if raw == "jsonb_ref":
        return "jsonb"
    return raw


def _normalize_db_type(data_type: str, udt_name: str | None) -> str:
    data_type = data_type.lower()
    udt_name = (udt_name or "").lower()
    if data_type == "timestamp with time zone":
        return "timestamptz"
    if data_type == "timestamp without time zone":
        return "timestamp"
    if data_type == "boolean":
        return "bool"
    if data_type in {"integer", "int4"}:
        return "int"
    if data_type == "uuid":
        return "uuid"
    if data_type in {"text", "character varying"}:
        return "text"
    if data_type == "jsonb" or udt_name == "jsonb":
        return "jsonb"
    return data_type


def _load_contract(path: Path) -> LLMWriteContract:
    return LLMWriteContract.model_validate(_read_json(path))


def _load_schema_snapshot(path: Path) -> SchemaSnapshot:
    payload = _read_json(path)
    columns = [
        ColumnInfo(
            name=col["name"],
            db_type=_normalize_db_type(col["type"], col.get("udt_name")),
            nullable=bool(col["nullable"]),
        )
        for col in payload.get("columns", [])
    ]
    return SchemaSnapshot(
        schema=payload["schema"],
        table=payload["table"],
        columns=columns,
        uniques=payload.get("uniques", []),
    )


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return db_url


def _redact_db_url(db_url: str) -> str:
    parsed = urlparse(db_url)
    if not parsed.password and not parsed.username:
        return db_url
    user = parsed.username or ""
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if user:
        netloc = f"{user}:***@{netloc}"
    return parsed._replace(netloc=netloc).geturl()


def _fetch_schema_from_db(db_url: str, schema: str, table: str) -> SchemaSnapshot:
    db_url = _normalize_db_url(db_url)
    try:
        conn = psycopg2.connect(db_url)
    except psycopg2.OperationalError as exc:
        raise RuntimeError(f"db connection failed for { _redact_db_url(db_url) }: {exc}") from exc
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type, udt_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            columns = [
                ColumnInfo(
                    name=row[0],
                    db_type=_normalize_db_type(row[1], row[2]),
                    nullable=(row[3] == "YES"),
                )
                for row in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT con.conname, array_agg(att.attname ORDER BY u.attposition) AS columns
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                JOIN unnest(con.conkey) WITH ORDINALITY AS u(attnum, attposition) ON true
                JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = u.attnum
                WHERE con.contype = 'u' AND nsp.nspname = %s AND rel.relname = %s
                GROUP BY con.conname
                ORDER BY con.conname
                """,
                (schema, table),
            )
            uniques = [list(row[1]) for row in cursor.fetchall()]
    finally:
        conn.close()
    return SchemaSnapshot(schema=schema, table=table, columns=columns, uniques=uniques)


def _compare_schema(shape: RowShape, snapshot: SchemaSnapshot) -> dict:
    expected_columns = shape.required_columns
    actual_columns = {col.name: col for col in snapshot.columns}

    missing_columns: list[str] = []
    type_mismatches: list[dict] = []
    nullability_mismatches: list[dict] = []

    for col in expected_columns:
        actual = actual_columns.get(col.name)
        if actual is None:
            missing_columns.append(col.name)
            continue
        expected_type = _normalize_contract_type(col.type)
        actual_type = actual.db_type
        if expected_type != actual_type:
            type_mismatches.append(
                {"column": col.name, "expected": expected_type, "actual": actual_type}
            )
        if col.nullable != actual.nullable:
            nullability_mismatches.append(
                {
                    "column": col.name,
                    "expected_nullable": col.nullable,
                    "actual_nullable": actual.nullable,
                }
            )

    expected_unique_sets = [frozenset(u) for u in shape.required_uniques]
    actual_unique_sets = [frozenset(u) for u in snapshot.uniques]
    missing_uniques = [
        list(u) for u in expected_unique_sets if u not in actual_unique_sets
    ]

    expected_names = {col.name for col in expected_columns}
    extra_columns = sorted([name for name in actual_columns if name not in expected_names])

    has_mismatch = bool(
        missing_columns or type_mismatches or nullability_mismatches or missing_uniques
    )
    return {
        "missing_columns": missing_columns,
        "type_mismatches": type_mismatches,
        "nullability_mismatches": nullability_mismatches,
        "missing_uniques": missing_uniques,
        "extra_columns": extra_columns,
        "has_mismatch": has_mismatch,
    }


def _render_report(
    *, contract_path: Path, shape_name: str, snapshot: SchemaSnapshot, diff: dict, mode: str
) -> str:
    lines: list[str] = []
    lines.append("LLM contract <-> DB parity report")
    lines.append(f"contract: {contract_path}")
    lines.append(f"shape: {shape_name}")
    lines.append(f"mode: {mode}")
    lines.append(f"table: {snapshot.schema}.{snapshot.table}")
    lines.append("")
    status = "PASS" if not diff["has_mismatch"] else "MISMATCH"
    lines.append(f"status: {status}")
    if diff["missing_columns"]:
        lines.append("")
        lines.append(f"missing columns ({len(diff['missing_columns'])}):")
        for col in diff["missing_columns"]:
            lines.append(f"  - {col}")
    if diff["type_mismatches"]:
        lines.append("")
        lines.append(f"type mismatches ({len(diff['type_mismatches'])}):")
        for entry in diff["type_mismatches"]:
            lines.append(
                f"  - {entry['column']}: expected={entry['expected']} actual={entry['actual']}"
            )
    if diff["nullability_mismatches"]:
        lines.append("")
        lines.append(f"nullability mismatches ({len(diff['nullability_mismatches'])}):")
        for entry in diff["nullability_mismatches"]:
            lines.append(
                "  - {column}: expected_nullable={expected_nullable} actual_nullable={actual_nullable}".format(
                    **entry
                )
            )
    if diff["missing_uniques"]:
        lines.append("")
        lines.append(f"missing unique constraints ({len(diff['missing_uniques'])}):")
        for cols in diff["missing_uniques"]:
            lines.append(f"  - {', '.join(cols)}")
    if diff["extra_columns"]:
        lines.append("")
        lines.append(f"extra columns (info only) ({len(diff['extra_columns'])}):")
        for col in diff["extra_columns"]:
            lines.append(f"  - {col}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compare live Postgres schema against LLM write-contract shapes.",
    )
    parser.add_argument("--contract", required=True, help="Path to LLM write contract JSON")
    parser.add_argument(
        "--shape",
        required=True,
        choices=["current_row_shape", "target_row_shape"],
        help="Row-shape section to compare",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["enforce", "report"],
        help="Enforce exits non-zero on mismatch; report always exits zero.",
    )
    parser.add_argument("--db-url", help="Postgres connection URL")
    parser.add_argument("--schema-snapshot", help="Path to a schema snapshot JSON")
    parser.add_argument("--output", help="Write report to file")
    args = parser.parse_args(argv[1:])

    if not args.db_url and not args.schema_snapshot:
        print("error: must provide --db-url or --schema-snapshot")
        return 2
    if args.db_url and args.schema_snapshot:
        print("error: choose only one of --db-url or --schema-snapshot")
        return 2

    contract_path = Path(args.contract)
    try:
        contract = _load_contract(contract_path)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"contract load failed: {exc}")
        return 2

    target = contract.targets[0]
    shape = getattr(contract, args.shape)

    try:
        if args.schema_snapshot:
            snapshot = _load_schema_snapshot(Path(args.schema_snapshot))
        else:
            snapshot = _fetch_schema_from_db(args.db_url, target.schema_name, target.table)
    except RuntimeError as exc:
        print(f"schema fetch failed: {exc}")
        return 2

    diff = _compare_schema(shape, snapshot)
    report = _render_report(
        contract_path=contract_path,
        shape_name=args.shape,
        snapshot=snapshot,
        diff=diff,
        mode=args.mode,
    )
    print(report, end="")
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")

    if args.mode == "enforce" and diff["has_mismatch"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
