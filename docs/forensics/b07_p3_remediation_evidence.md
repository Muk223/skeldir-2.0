# B0.7-P3 Follow-Up Corrective Action Evidence

Date: 2026-02-07
Branch: `main`
Scope authority: `main` code + CI job logs + workflow status checks

## Scientific Framing

### Follow-up hypotheses and outcomes
1. **H-P3-F01 (Hermetic violation in choke point): Confirmed (initially true), then remediated.**
   - Failing main push run `21786102869`, job `62857781342` logged:
     - `backend/app/llm/provider_boundary.py:12 forbidden:importlib`
     - `backend/app/llm/provider_boundary.py:791 forbidden:importlib.import_module`
2. **H-P3-F02 (Mainline truth inconsistent): Confirmed (initially true), then remediated.**
   - `test_b07_p3_provider_controls.py` passed in runtime-proof job while overall run still failed due to hermetic/determinism guardrails.
3. **H-P3-F03 (Governance coverage gap): Confirmed (initially true), then remediated.**
   - Branch protection initially required only `B0.7 P2 Runtime Proof (LLM + Redaction)`.
   - Updated required checks now include `Celery Foundation B0.5.1` (where hermetic/determinism enforcers run).
4. **H-P3-F04 (Single write path underdetermined by grep): Confirmed (initially true), then remediated.**
   - Added CI-enforced AST scanner + negative-control test for `llm_api_calls` write path.
5. **H-P3-F05 (Boundary exclusivity weakened by dynamic loading): Confirmed (initially true), then remediated.**
   - Removed dynamic import path in choke point and replaced with deterministic static loading.

## Root Cause Validation
1. `provider_boundary.py` used dynamic import to load `aisuite`; this violated hermetic import policy.
2. Determinism scanner additionally flagged `datetime.now(...)` in the same runtime module.
3. Required status checks were too narrow for production-grade closure.
4. Prior single-write proof was grep-based and not fail-closed.

## Corrective Remediations

### 1) Hermetic + deterministic choke point
1. `backend/app/llm/provider_boundary.py` no longer uses `importlib`.
2. `aisuite` loading is static and deterministic:
   - module import guard at `backend/app/llm/provider_boundary.py:25`
   - explicit fail-closed path `RuntimeError("aisuite_not_installed")` at `backend/app/llm/provider_boundary.py:803`
3. Replaced runtime entropy calls:
   - added DB clock helper `_db_now(...)` at `backend/app/llm/provider_boundary.py:94`
   - replaced all `datetime.now(...)` usage with `_db_now(...)` calls.

### 2) Single-write-path invariant upgraded to CI-enforced rule
1. Added scanner: `scripts/ci/enforce_llm_api_call_single_write_path.py`.
2. Added test with negative control + repo-state pass:
   - `backend/tests/test_b07_p3_single_write_path_enforcement.py`
   - fixture: `backend/tests/fixtures/forbidden_llm_api_call_write_fixture.txt`
3. CI runtime-proof job now executes scanner and test:
   - step `Enforce llm_api_calls single write path`.

### 3) Governance closure (required checks)
1. Branch protection for `main` now requires:
   - `B0.7 P2 Runtime Proof (LLM + Redaction)`
   - `Celery Foundation B0.5.1`
2. `Celery Foundation B0.5.1` includes:
   - `Enforce hermetic runtime imports (Phase 5)`
   - `Enforce runtime determinism (Phase 5)`

## CI Evidence (Authoritative)

### A) Initial failure proving the defect
1. Run (failed): `https://github.com/Muk223/skeldir-2.0/actions/runs/21786102869`
2. Failing job: `https://github.com/Muk223/skeldir-2.0/actions/runs/21786102869/job/62857781342`
3. Hermetic scanner findings in log:
   - `backend/app/llm/provider_boundary.py:12 forbidden:importlib`
   - `backend/app/llm/provider_boundary.py:791 forbidden:importlib.import_module`

### B) Intermediate determinism failure proving second defect
1. Run (branch validation): `https://github.com/Muk223/skeldir-2.0/actions/runs/21786980185/job/62859961999`
2. Determinism findings in log:
   - `backend/app/llm/provider_boundary.py:* forbidden:datetime.now`

### C) Final mainline green push proving closure
1. Run (pass): `https://github.com/Muk223/skeldir-2.0/actions/runs/21787059530`
2. Head SHA on run: `86e8df8da0cff89c82f6f8ea41e6d2a4cf1ee3f6`
3. Runtime-proof job (pass): `https://github.com/Muk223/skeldir-2.0/actions/runs/21787059530/job/62860186610`
   - `Enforce llm_api_calls single write path` -> success (`Violations: 0`)
   - `Run B0.7 P3 provider controls gate` -> success
   - `backend/tests/test_b07_p3_provider_controls.py` -> `10 passed, 136 warnings in 2.65s`
   - `Verify B0.7 P2 artifact and log redaction hygiene` -> `B0.7 P2 redaction hygiene scan passed`
4. Celery foundation job (pass): `https://github.com/Muk223/skeldir-2.0/actions/runs/21787059530/job/62860186603`
   - `Enforce hermetic runtime imports (Phase 5)` -> success
   - `Enforce runtime determinism (Phase 5)` -> success

## Branch Protection Proof
Command used:
```powershell
gh api repos/Muk223/skeldir-2.0/branches/main/protection
```

Observed required status checks:
1. `B0.7 P2 Runtime Proof (LLM + Redaction)`
2. `Celery Foundation B0.5.1`

## Commit Evidence
1. `136e2b7` - static `aisuite` loading + single-write-path enforcement tooling/tests/CI wiring
2. `c7318af` - deterministic DB-time refactor in provider boundary
3. `86e8df8da0cff89c82f6f8ea41e6d2a4cf1ee3f6` - merged to `main` and validated by fully green `push` run `21787059530`

## Exit-Gate Disposition
1. EG-P3-CA1 Hermetic Determinism Gate: **PASS**
2. EG-P3-CA2 Mainline Governance Closure Gate: **PASS**
3. EG-P3-CA3 Provider Boundary Exclusivity Gate: **PASS**
4. EG-P3-CA4 Single Write Path Enforcement Gate: **PASS**
5. EG-P3-CA5 Regression-Proof Functional Controls Gate: **PASS**

## Verdict
B0.7-P3 follow-up corrective action is empirically complete on `main` under the stated authority model (`main` code + green `push` CI + artifacts/logs).
