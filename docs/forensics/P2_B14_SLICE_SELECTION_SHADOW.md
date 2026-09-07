# Phase II Slice 1 — B14 Privacy-Plane Consolidation (Shadow)

**State:** SHADOW (P2-C3). New lane produces evidence only; merge authority
unchanged (contract v1.21.0, 80/80 contexts intact).
**Branch:** `p2-b14-consolidation-shadow` from `origin/main@12db0403`.
**Directive:** CI-INFRASTRUCTURE THROUGHPUT REMEDIATION — PHASE II (governing).
**Baseline:** Phase I handoff (current-state) + greenfield audit (historical only;
every number below re-measured live-offline on 2026-09-07/08, never copied).

## 1. Causal-spine trace (s1.2)

```
developer commit
  -> GitHub pull_request / push / merge_group -> candidate SHA (ADJUDICATED_SHA)
  -> ci.yml b14-p0..b14-p7 (incumbent, required, 8 cold envs, 7 PG boots, 7 replays)
  -> b14-privacy-consolidated.yml (shadow, non-required, 1 env, 1 PG boot, 1 replay)
       -> shared immutable substrate (checkout@SHA, py3.11, pip reqs, pg15-alpine, template@alembic-head)
       -> 7 template-cloned consequence-isolated DBs + p6 static
       -> 8 verbatim proof sections -> proof_results.jsonl ledger
       -> aggregate verdict (GREEN iff 8/8 rc=0, same SHA, clean JUnit)
  -> compare_b14_equivalence.py (same-SHA comparator, verdict+failing-node+NC+env)
  -> validate_b14_migration.py (SHADOW -> DUAL -> CUTOVER monotonic gate)
  -> repository governance contract + live branch protection (unchanged in SHADOW)
  -> merge_group ALLGREEN -> protected main
```

Per-edge authority: producers/consumers are the files above; SHA binding is
`ADJUDICATED_SHA` (checkout ref + ledger sha + comparator claim, all three
compared); immutable inputs are lockfile bytes + PG image + alembic graph;
mutable inputs are the 7 cloned DBs (per-proof) + ledger (append-only);
cache authority is setup-python pip (hit==miss, install still unconditional);
proof artifact identity is `b14-consolidated-artifacts` (never overwrites
`b14-pN-runtime-artifacts`); only the aggregate step influences the shadow
check; NOTHING in this lane can influence merge authority (not in contract).

## 2. Graph A — proof ownership (I-1)

Predecessor (ci.yml, required): b14-p0..b14-p7 -> I-1 tenant isolation ->
8 required contexts (contract v1.21.0) -> enforcer scripts +
15 pytest files (3 p0 + 2x(p1..p5 enforcer+runtime) + 1 p6 + 1 p7) ->
negative controls (p1-p5 enforcer suites, p5/p6/p7 --simulate-regression,
p7 artifact scan canary). Successor: `B1.4 Privacy Consolidated Plane`
(single check). Mapping 8->1 recorded in code (`PREDECESSOR_PROOFS`,
`EXPECTED_JUNIT`) and enforced by ledger (8 rows) + comparator (8 proofs) +
migration gate (CUTOVER requires corpus). No I-1 obligation orphaned; R2 and
B2.4-P9 co-owners untouched (different workflows, out of slice).

## 3. Graph B — environment physics

Measured on origin/main@12db0403 (scripts in /tmp, re-runnable):
- ci.yml: 69 jobs; dominant signature group = 29 jobs
  (ubuntu-latest, py3.11, PG service, pip install, alembic); B14 contributes
  7 of those + p6 (no PG, static).
- ci.yml raw: 121 `pip install` lines, 46 `services:` blocks, 60 setup-python,
  59 alembic, 169 pytest invocations; repo-wide 352 pip installs (unchanged).
- Incumbent B14 slice per required event: 8 checkouts + 8 py setups +
  8 pip double-installs + 7 PG boots + 7 full migration replays (169 revs each).
- Consolidated: 1 checkout + 1 py setup + 1 pip double-install + 1 PG boot +
  1 replay + 7 `CREATE DATABASE ... TEMPLATE` clones.
- Delta (cohort): cold dependency builds 8->1 (-87.5%, target -60%);
  PG boots 7->1 (-85.7%, target -50%); migration replays 7->1 (-85.7%).
  Proof execution unchanged (verbatim commands). 169 revisions / 2 heads bound
  in EnvSig digest `0a4ed59a...` (recompute per run; any drift REDs comparator).

DB-reuse classification (s4.7): reusable = checkout/py/deps/PG server/schema
(construction is not the proof); must-remain-fresh-per-proof = consequence
rows (tenant/role/session state). Template carries schema+roles, zero rows;
clones start empty like fresh servers. Cluster-level roles (created once by
the single replay) are the one shared mutable surface: accepted because B14
tests assert row visibility under roles, never role DDL; the equivalence
corpus (incl. red-team) must confirm, else the slice is rejected (H-P2-09).

## 4. Graph C — live authority (offline-verifiable part)

Contract v1.21.0: 80 contexts incl. 8 B14 (listed s3). ci.yml fires
pull_request+push(main,develop)+merge_group+dispatch with event-keyed
concurrency; all 8 B14 jobs admitt merge_group (no `if:`). Shadow workflow
mirrors triggers/concurrency/ADJUDICATED_SHA checkout check; its check name
is disjoint from all 80 (no collision, no spoofing). Live branch protection /
merge queue / check-run SHA verification is OUTSIDE the offline boundary and
is recorded as the fresh live-control-plane audit step in s7.

## 5. Slice selection (empirical, s4.3)

Candidates: B13 (9 jobs, same signature, larger blast radius, active B2.5-P14
neighborhood churn) / B12 (4 jobs, smaller saving) / B21-no-migration group
(11 jobs, no migration-replay saving) / B14 (8 jobs, one invariant I-1,
dominant signature, B1.4 quiescent vs B2.x flight, 7 PG boots + 7 replays).
Selected B14: smallest slice with meaningful duplication + single-invariant
ownership + maximal per-job saving density + minimal interaction risk.
H-P2-01..11 dispositions: H-01 capacity floor CONFIRMED for cohort (8-way
queue+setup per event); H-02 cold multiplicity CONFIRMED (87.5% removable);
H-03 reuse opportunity CONFIRMED pending corpus; H-04 deadlock avoided by
new-context (not rename) migration; H-05 stable-context REJECTED for B14
(8->1 cannot keep names without wrapper ambiguity); H-06 shadow load +1 run
(~+3-5% vs 21-31 bursts, inside P2-C7 20% budget, monitored); H-07 verdict-only
SURVIVES by design (comparator compares node IDs + NC + env); H-08 cache
collision mitigated (no new cache keys; pip cache hit==miss, install
unconditional); H-09 DB overreach tested by corpus, not asserted; H-10 graph
shape unchanged (needs: edges inside ci.yml untouched); H-11 wrapper severance
falsified by ledger NC (7/8 RED, rc-laundering RED, stale-SHA RED).

Pipefail note (MEASURED 2026-09-07, shadow run 34140659251): GHA `run` steps
execute under `/usr/bin/bash -e {0}` with NO pipefail, identically in both
lanes. `pytest ... | tee` therefore reports tee's exit code. Verbatim
construction keeps verdict functions identical by design; the ledger +
JUnit-presence + aggregate layers fail closed on masked crashes (proven
live: p6 crash -> missing junit -> aggregate RED). Changing pipes would
alter verdict semantics (forbidden in-slice); a governance-owned pipefail
hygiene pass is deferred as R-P2-06.

Incumbent p6 vacuity (MEASURED): backend conftest B0.5.3.3 Gate C (from PR
#713) requires DATABASE_URL in CI, but ci.yml job b14-p6-proof-plane-binding
sets none (static job, no PG service). Its pytest crashes at conftest import
on every run, masked by `| tee`, job GREEN. Evidence: run 34047052521
artifact b14-p6-runtime-artifacts = 816 bytes, no JUnit. The consolidated
lane provisions p6 an empty migrated clone (strictly stronger witness; same
invariant, executed suite) and the identical ci.yml p6 env fix is queued for
the DUAL change. Comparator verdicts on green SHAs still match (green/green);
a p6-test red-team fault will correctly diverge old-green(vacuous)/new-red
with this diagnosis attached.

## 6. Non-vacuity (all green on this branch)

- comparator --self-test: 9/9 (wrong-SHA, missing old/new, both divergences,
  stale artifact, altered test set, omitted NC).
- migration --self-test: 9/9 (premature-retirement REDs, lawful states GREEN).
- consolidation NC: 13/13 (ledger severance/stale/launder, env foreign-state,
  provisioner isolation).
- physics guard: 65/65 workflows conform (shadow exemptions honored).
- migration gate on live tree: GREEN state=SHADOW.

## 7. Live corpus plan (s4.5, NOT YET COLLECTED — owner-gated)

Collect on disposable + ordinary PRs (no freeze, no rebase, no bypass):
10 pairs (>=3 tenant/privacy-relevant where B14 is relevant, >=2 docs-only,
>=2 merge_group speculative SHAs, >=1 red-team mutation e.g. RLS policy
drop in a Branch, reverted after). Each records event type, candidate SHA,
old run/job IDs (8x), new run/job ID, old+new verdicts, proof identities,
NC outcomes, env digest, queue/execution times. Comparator adjudicates each;
P2-C7 monitored (incumbent queue p50 vs matched baseline; halt shadow on
>20% degradation). Promotion (DUAL then CUTOVER) is a separate governed
change with admin branch-protection update + contract v1.22.0, only after
corpus GREEN + live-control-plane audit (check SHAs, protection, queue).

## 8. Quantitative status (honest, P2-C9)

Cohort-level (this slice): C2-07 -87.5% cold builds (target -60%) and C2-08
-85.7% DB boots (target -50%) by construction count; runtime-log
confirmation required from first shadow runs. Repo-wide C2-09/C2-10
(queue<4m/-50%, wall<=15m/-40%) CANNOT close on one 8-job slice (~10% of
check-runs); they close across slices 1..N using this lane as the proven
migration machine. Claiming otherwise would be narrative waiver.
Next slices (same machine): B13 (9 jobs), B12 (4), B21 cohort (6-7).

## 9. First-red ledger (this branch)

- env-sig scan bound 40/171 revisions (annotated-assignment regex) -> caught
  by audit-count cross-check (169 expected) -> fixed, re-verified 169/169.
- aggregator NC initially RED-on-legitimate-enforcer-failure (rc=1/junit-green
  treated as mismatch) -> root-caused (enforcers emit no JUnit) -> narrowed to
  wrapper-green direction only, re-verified 13/13 (now 14/14 with masked-crash).
- comparator self-test lambdas refactored for clarity before first run
  (no behavioral red).
- LIVE shadow run 34140659251 (SHA 4a7ff527, PR #721): aggregate RED with
  exact diagnosis `missing-artifact:p6/junit.enforcer.xml` +
  `proof-failed:p7 rc=1`. Classified: p7 = candidate-lane defect (bare p7
  enforcer used default artifacts/b14_p7 output root; fixed with explicit
  --artifacts-dir); p6 = incumbent CI defect (conftest Gate C vs missing
  DATABASE_URL, crash masked by tee, job green-vacuous; evidence 816-byte
  artifact). Lane failed closed precisely as designed; no engineer action
  forced (shadow, P2-C3).
- LIVE shadow run 34141216197 (SHA df9ea248): p6 GREEN with real JUnit
  (clone fix works); p7 rc=1 persists -> root-caused to the p7 TEST itself
  hardcoding `artifacts/b14_p7` as its report root (product-test code, out
  of Phase II scope to rewrite). Fix: lane-side relocation copies after
  pytest (proof executes byte-identically; `set -e` keeps it fail-closed).
  Scan confirms p0-p6 tests have no such hardcoded roots.
- LIVE shadow run 34141912972 (SHA 5da45dbc, PR #721): **GREEN** — 8/8
  ledger rows rc=0 on one SHA, aggregate GREEN, JUnit + NC evidence present.
  Lane works end-to-end (1 env build, 1 PG boot, 1 migration, 8 clones,
  15 pytest files, enforcers, scans). Awaiting incumbent CI run 34141912982
  on the same SHA for pair #1.
- PAIR #1 (SHA 5da45dbc): old CI 34141912982 B14 8/8 success + new shadow
  34141912972 success. Comparator with live conclusions: 7/8 proofs identical
  node IDs (p0 6/4/2, p1 5, p2 4, p3 9, p4 5, p5 4, p7 3) and green verdicts
  bound proof-level; env authority matched; single precise RED
  `missing-old-proof:p6/junit.enforcer.xml` (incumbent vacuity, disposition
  recorded; DUAL bundles the ci.yml p6 env fix). Persisted in
  `docs/forensics/p2_b14_equivalence_corpus.json` (1/10 pairs; CUTOVER needs
  10 with comparator GREEN each — gate enforces).
  Measured cohort physics: old 4707 slot-s (queue med 498s, max 930s wall)
  vs new 141 slot-s (queue 40s, exec 101s) = **-97% slot-time, -85% wall**.
  P2-C7: incumbent B14 queue (212-856s) within Phase-I baseline band
  (540-1260s med); +1 shadow job (~2% of 51-run burst) shows no systematic
  distortion. Unrelated reds on the pair PR (B2.1-P4 perf threshold
  5.2552>=5.0, cascade to Drift Gate, B0.4 10-min silent timeout):
  classified runner-contention/external; rerun requested to confirm flake.

## 10. Residual debt register (Phase II slice 1)

R-P2-01: live paired corpus uncollected (needs pushes + merge_group entries).
R-P2-02: DUAL/CUTOVER unexecuted (needs admin + corpus GREEN).
R-P2-03: runtime-log construction counts (cache misses, PG boots, setup
slot-minutes) pending first shadow runs.
R-P2-04: queue/wall repo-wide closure pending slices 2..N.
R-P2-05: role-DDL assumption (s3) pending red-team confirmation.
R-P2-06: pipefail hygiene question deferred (s5).
