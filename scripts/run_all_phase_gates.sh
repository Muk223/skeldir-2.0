#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-evidence_registry}"

python scripts/phase_gates/check_runtime_phase.py --root "$ROOT"
python scripts/phase_gates/check_contract_phase.py --root "$ROOT"
python scripts/phase_gates/check_statistics_phase.py --root "$ROOT"
python scripts/phase_gates/check_privacy_phase.py --root "$ROOT"
python scripts/phase_gates/check_chain_phase.py --root "$ROOT"
