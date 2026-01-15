# B055 Phase 5 Remediation Evidence

## Repo Pin (Adjudicated)
- PR: https://github.com/Muk223/skeldir-2.0/pull/22
- ADJUDICATED_SHA: see bundle `MANIFEST.json` field `adjudicated_sha`
- Artifact rule: `b055-evidence-bundle-${ADJUDICATED_SHA}`
- CI run identity: authoritative in bundle `MANIFEST.json` (`workflow_run_id`, `run_attempt`)

## Enforcement (Fail-Closed)
- Hermeticity scan log: bundle `LOGS/hermeticity_scan.log`
- Determinism scan log: bundle `LOGS/determinism_scan.log`

## Cohesion Proofs (Tests)
- Proof log: bundle `LOGS/pytest_b055.log`
- Coverage includes:
  - `backend/tests/test_b055_llm_payload_fidelity.py`
  - `backend/tests/test_b055_matview_boundary.py`
  - `backend/tests/test_b055_tenant_propagation.py`
  - `backend/tests/test_b052_queue_topology_and_dlq.py`
  - `backend/tests/test_b055_llm_worker_stubs.py`

## Evidence Bundle (Phase 4 Adjudication)
- Generator: `scripts/ci/b055_evidence_bundle.py`
- Artifact name rule: `b055-evidence-bundle-${ADJUDICATED_SHA}`
- Manifest fields required:
  - `adjudicated_sha`
  - `pr_head_sha`
  - `github_sha`
  - `workflow_run_id`
  - `run_attempt`
- Required logs present in bundle:
  - `LOGS/hermeticity_scan.log`
  - `LOGS/determinism_scan.log`
  - `LOGS/pytest_b055.log`
  - `LOGS/migrations.log`

## Adjudication Proof (Authority Model)
- The authoritative binding between CI run and merge candidate is the bundle `MANIFEST.json`.
- Evidence documents must not hardcode SHA/run IDs; they must defer to the manifest
  in the uploaded CI artifact for the adjudicated run.
- The current adjudication evidence (PR/run/manifest excerpts and log snippets)
  is recorded in the latest Phase 5 evidence pack under `docs/forensics/`.
