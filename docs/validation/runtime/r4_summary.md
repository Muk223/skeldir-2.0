# R4 Worker Failure Semantics Summary (Truth Anchor)

## Status

R4 = **IN PROGRESS** as of:

- **Candidate SHA:** `c84b4687c9d2bbd862ce624d4225829cd56c3c54`
- **CI run:** https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123
- **Generated at:** `2025-12-28T20:28:00.938838+00:00`

## Run Configuration (from harness log)

- `broker_url` = `sqla+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `result_backend` = `db+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `acks_late` = `True`
- `reject_on_worker_lost` = `True`
- `acks_on_failure_or_timeout` = `True`
- `prefetch_multiplier` = `1`
- `tenant_a` = `0e276637-8872-5b76-a68b-5a9f82f60211`
- `tenant_b` = `a1744178-bcf2-53ad-a235-5f531ccb6595`

## Exit Gates (Pass Matrix)

| Gate | Description | Status |
|------|-------------|--------|
| EG-R4-FIX-0 | Instrument integrity (SHA + config + verdicts) | PASS |
| EG-R4-FIX-1 | Poison retries proven (attempts_min_per_task >= 2) | FAIL |
| EG-R4-FIX-2 | Crash physics proven (barrier→kill→exit→restart→redelivery) | FAIL |
| EG-R4-FIX-3 | Redelivery accounting (redelivery_observed_count == N) | FAIL |
| EG-R4-FIX-4 | RLS + runaway + least-privilege still pass | FAIL |

## Evidence (Browser-Verifiable Logs)

This run prints, to CI logs, one `R4_VERDICT_BEGIN/END` JSON block per scenario.

Log step containing verdict blocks: `Run R4 harness` in `.github/workflows/r4-worker-failure-semantics.yml`.

Crash proof markers printed in logs (per task_id):

- `R4_S2_BARRIER_OBSERVED`
- `R4_S2_KILL_ISSUED`
- `R4_S2_WORKER_EXITED`
- `R4_S2_WORKER_RESTARTED`
- `R4_S2_REDELIVERED`

## Key Verdicts

### S1 PoisonPill (N=10)
```json
{
  "N": 10,
  "candidate_sha": "c84b4687c9d2bbd862ce624d4225829cd56c3c54",
  "db_truth": {},
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123",
  "scenario": "S1_PoisonPill",
  "tenant_a": "0e276637-8872-5b76-a68b-5a9f82f60211",
  "tenant_b": "a1744178-bcf2-53ad-a235-5f531ccb6595",
  "worker_observed": {
    "error": "TimeoutError: Timed out waiting for Celery results"
  }
}
```

### S2 CrashAfterWritePreAck (N=10)
```json
{
  "N": 10,
  "candidate_sha": "c84b4687c9d2bbd862ce624d4225829cd56c3c54",
  "db_truth": {
    "attempts": {
      "attempts_distribution": {},
      "attempts_max_per_task": 0,
      "attempts_min_per_task": 0,
      "attempts_total": 0,
      "task_count_observed": 0
    },
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123",
  "scenario": "S2_CrashAfterWritePreAck",
  "tenant_a": "0e276637-8872-5b76-a68b-5a9f82f60211",
  "tenant_b": "a1744178-bcf2-53ad-a235-5f531ccb6595",
  "worker_observed": {
    "crash_physics": {
      "barrier_observed_count": 0,
      "kill_issued_count": 0,
      "redelivery_observed_count": 0,
      "worker_exited_count": 0,
      "worker_restarted_count": 0
    },
    "kill_issued": true,
    "kill_sig": 9,
    "redelivery_observed_count": 0,
    "worker_exit_codes": [],
    "worker_pid_after": 2428,
    "worker_pid_before": 2428,
    "worker_pid_restarts": []
  }
}
```

### S3 RLSProbe (N=1)
```json
{
  "N": 1,
  "candidate_sha": "c84b4687c9d2bbd862ce624d4225829cd56c3c54",
  "db_truth": {},
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123",
  "scenario": "S3_RLSProbe",
  "tenant_a": "0e276637-8872-5b76-a68b-5a9f82f60211",
  "tenant_b": "a1744178-bcf2-53ad-a235-5f531ccb6595",
  "worker_observed": {
    "error": "OperationalError: (psycopg2.OperationalError) connection to server at \"127.0.0.1\", port 5432 failed: FATAL:  remaining connection slots are reserved for roles with the SUPERUSER attribute\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)"
  }
}
```

### S4 RunawayNoStarve (sentinels N=10)
```json
{
  "N": 10,
  "candidate_sha": "c84b4687c9d2bbd862ce624d4225829cd56c3c54",
  "db_truth": {},
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123",
  "scenario": "S4_RunawayNoStarve",
  "tenant_a": "0e276637-8872-5b76-a68b-5a9f82f60211",
  "tenant_b": "a1744178-bcf2-53ad-a235-5f531ccb6595",
  "worker_observed": {
    "error": "OperationalError: (psycopg2.OperationalError) connection to server at \"127.0.0.1\", port 5432 failed: FATAL:  remaining connection slots are reserved for roles with the SUPERUSER attribute\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)"
  }
}
```

### S5 LeastPrivilege (N=1)
```json
{
  "N": 1,
  "candidate_sha": "c84b4687c9d2bbd862ce624d4225829cd56c3c54",
  "db_truth": {},
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559086123",
  "scenario": "S5_LeastPrivilege",
  "tenant_a": "0e276637-8872-5b76-a68b-5a9f82f60211",
  "tenant_b": "a1744178-bcf2-53ad-a235-5f531ccb6595",
  "worker_observed": {
    "error": "OperationalError: (psycopg2.OperationalError) connection to server at \"127.0.0.1\", port 5432 failed: FATAL:  remaining connection slots are reserved for roles with the SUPERUSER attribute\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)"
  }
}
```

## Where the Evidence Lives

- Workflow: `.github/workflows/r4-worker-failure-semantics.yml`
- Harness: `scripts/r4/worker_failure_semantics.py`
- Summary generator: `scripts/r4/render_r4_summary.py`

