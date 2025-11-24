#!/usr/bin/env python3
"""
Privacy phase gate.

Verifies runtime PII redaction and, when available, database/DLQ guardrail logs.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from utils import fail, latest_with_prefix, load_json, ok, parse_args  # noqa: E402

PII_KEYS = {
    "email",
    "phone",
    "address",
    "ip",
    "ssn",
    "credit_card",
    "passport",
    "billing_address",
    "shipping_address",
    "customer_email",
    "customer_phone",
}


def _collect_pii(data, prefix="root"):
    found = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}"
            if key.lower() in PII_KEYS:
                found[path] = value
            elif isinstance(value, (dict, list)):
                found.update(_collect_pii(value, path))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            path = f"{prefix}[{idx}]"
            if isinstance(value, (dict, list)):
                found.update(_collect_pii(value, path))
    return found


def _assert_log_clean(path: Path) -> None:
    text = path.read_text(encoding="utf-8").upper()
    if any(token in text for token in ("FAIL", "ERROR", "TRACEBACK")):
        fail(f"{path} contains failure markers")


def main() -> None:
    args = parse_args()
    root: Path = args.root
    privacy_dir = root / "privacy"

    before = privacy_dir / "raw_payload_before.json"
    after = privacy_dir / "raw_payload_after.json"
    if not before.is_file() or not after.is_file():
        fail("raw_payload_before.json / raw_payload_after.json missing")

    before_json = load_json(before)
    after_json = load_json(after)

    before_pii = _collect_pii(before_json)
    after_pii = _collect_pii(after_json)
    if not before_pii:
        fail("Before payload contains no PII keys – test input invalid")

    failures = []
    for path, original in before_pii.items():
        redacted = after_pii.get(path)
        if redacted != "[REDACTED]":
            failures.append((path, original, redacted))

    if failures:
        for path, original, redacted in failures:
            print(
                f"[DETAIL] {path} not redacted: before={original!r}, after={redacted!r}"
            )
        fail("Runtime PII redaction failed for one or more keys")

    ok("Runtime PII redaction validated via before/after payloads")

    # Optional: database guardrail tests (when present)
    db_candidates = sorted((root / "privacy").glob("pii_guardrail_db_tests_*"))
    if db_candidates:
        db_log = db_candidates[-1]
        _assert_log_clean(db_log)
        ok(f"Database PII guardrails validated via {db_log}")
    else:
        print("[WARN] No pii_guardrail_db_tests_* artifact found; skipping DB checks")

    # Optional: DLQ logs
    dlq_candidates = sorted((root / "privacy").glob("dlq_population_log_*"))
    if dlq_candidates:
        dlq_log = dlq_candidates[-1]
        _assert_log_clean(dlq_log)
        ok(f"DLQ population verified via {dlq_log}")
    else:
        print("[WARN] No dlq_population_log_* artifact found; skipping DLQ checks")

    ok("Privacy phase gate: PASS")


if __name__ == "__main__":
    main()
