# R4 Worker Failure Semantics Summary (Truth Anchor)

## Status

R4 = **IN PROGRESS** as of:

- **Candidate SHA:** `0a6da1df6e7ced2df1b8c208ac197c940e587375`
- **CI run:** https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836
- **Generated at:** `2025-12-28T22:06:53.067153+00:00`

## Run Configuration (from harness log)

- `broker_url` = `sqla+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `result_backend` = `db+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `acks_late` = `True`
- `reject_on_worker_lost` = `True`
- `acks_on_failure_or_timeout` = `True`
- `prefetch_multiplier` = `1`
- `tenant_a` = `3efe4701-bba8-5314-bc2d-7d9665127a31`
- `tenant_b` = `5593ce4e-870f-5652-b7b3-babfe3f29621`

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
  "candidate_sha": "0a6da1df6e7ced2df1b8c208ac197c940e587375",
  "db_truth": {
    "attempts": {
      "attempts_distribution": {
        "44": 1,
        "45": 4
      },
      "attempts_max_per_task": 45,
      "attempts_min_per_task": 44,
      "attempts_total": 224,
      "task_count_observed": 5
    },
    "worker_failed_jobs": {
      "max_retry_count": 0,
      "rows": 5,
      "rows_total": 209
    },
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836",
  "scenario": "S1_PoisonPill",
  "tenant_a": "3efe4701-bba8-5314-bc2d-7d9665127a31",
  "tenant_b": "5593ce4e-870f-5652-b7b3-babfe3f29621",
  "worker_observed": {
    "dlq_rows_observed": 5
  }
}
```

### S2 CrashAfterWritePreAck (N=10)
```json
{
  "N": 10,
  "candidate_sha": "0a6da1df6e7ced2df1b8c208ac197c940e587375",
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
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836",
  "scenario": "S2_CrashAfterWritePreAck",
  "tenant_a": "3efe4701-bba8-5314-bc2d-7d9665127a31",
  "tenant_b": "5593ce4e-870f-5652-b7b3-babfe3f29621",
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
    "worker_pid_after": 4457,
    "worker_pid_before": 4457,
    "worker_pid_restarts": []
  }
}
```

### S3 RLSProbe (N=1)
```json
{
  "N": 1,
  "candidate_sha": "0a6da1df6e7ced2df1b8c208ac197c940e587375",
  "db_truth": {
    "pg_connections_error_snapshot": {
      "by_user_state": [
        {
          "count": 23,
          "state": "idle",
          "usename": "app_user"
        },
        {
          "count": 1,
          "state": "active",
          "usename": "r4_admin"
        }
      ],
      "max_connections": 100
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836",
  "scenario": "S3_RLSProbe",
  "tenant_a": "3efe4701-bba8-5314-bc2d-7d9665127a31",
  "tenant_b": "5593ce4e-870f-5652-b7b3-babfe3f29621",
  "worker_observed": {
    "error": "TimeoutError: The operation timed out."
  }
}
```

### S4 RunawayNoStarve (sentinels N=10)
```json
{
  "N": 10,
  "candidate_sha": "0a6da1df6e7ced2df1b8c208ac197c940e587375",
  "db_truth": {
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836",
  "scenario": "S4_RunawayNoStarve",
  "tenant_a": "3efe4701-bba8-5314-bc2d-7d9665127a31",
  "tenant_b": "5593ce4e-870f-5652-b7b3-babfe3f29621",
  "worker_observed": {
    "runaway_outcome": "TimeoutError",
    "sentinel_rows_observed": 0
  }
}
```

### S5 LeastPrivilege (N=1)
```json
{
  "N": 1,
  "candidate_sha": "0a6da1df6e7ced2df1b8c208ac197c940e587375",
  "db_truth": {
    "pg_connections_error_snapshot": {
      "by_user_state": [
        {
          "count": 10,
          "state": "idle",
          "usename": "app_user"
        },
        {
          "count": 1,
          "state": "active",
          "usename": "r4_admin"
        }
      ],
      "max_connections": 100
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20560071836",
  "scenario": "S5_LeastPrivilege",
  "tenant_a": "3efe4701-bba8-5314-bc2d-7d9665127a31",
  "tenant_b": "5593ce4e-870f-5652-b7b3-babfe3f29621",
  "worker_observed": {
    "error": "TimeoutError: The operation timed out."
  }
}
```

## Where the Evidence Lives

- Workflow: `.github/workflows/r4-worker-failure-semantics.yml`
- Harness: `scripts/r4/worker_failure_semantics.py`
- Summary generator: `scripts/r4/render_r4_summary.py`

