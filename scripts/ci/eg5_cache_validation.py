"""
EG5 cache validation: prove /health/worker cache reuse via HTTP.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any

import requests


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.1)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser.parse_args()


def _parse_body(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def main() -> int:
    args = _parse_args()
    results: list[dict[str, Any]] = []

    with requests.Session() as session:
        for attempt in range(1, 4):
            resp = session.get(args.url, timeout=args.timeout_seconds)
            body = _parse_body(resp.text)
            print(f"eg5_cache_validation_attempt_{attempt}_begin", flush=True)
            print(resp.status_code, flush=True)
            print(resp.text, flush=True)
            print(f"eg5_cache_validation_attempt_{attempt}_end", flush=True)
            results.append(
                {
                    "attempt": attempt,
                    "status_code": resp.status_code,
                    "body": body,
                }
            )
            time.sleep(args.delay_seconds)

    expected = [False, True, True]
    cached_values = [r["body"].get("cached") for r in results]
    if cached_values != expected:
        print(
            f"eg5_cache_validation_failed cached_values={cached_values} expected={expected}",
            flush=True,
        )
        return 1

    print("eg5_cache_validation_passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
