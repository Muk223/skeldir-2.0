# R4 Worker Failure Semantics Summary (Truth Anchor)

## Status

R4 = **IN PROGRESS** as of:

- **Candidate SHA:** `648c89415f3dd1ee6beb92246d0c34c374703224`
- **CI run:** https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220
- **Generated at:** `2025-12-28T21:42:32.082444+00:00`

## Run Configuration (from harness log)

- `broker_url` = `sqla+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `result_backend` = `db+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `acks_late` = `True`
- `reject_on_worker_lost` = `True`
- `acks_on_failure_or_timeout` = `True`
- `prefetch_multiplier` = `1`
- `tenant_a` = `e20d1cdf-3171-53c7-bbde-ca42fee1c093`
- `tenant_b` = `4e8dde8a-f66e-5ac3-8a22-2c9107763cfa`

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
  "candidate_sha": "648c89415f3dd1ee6beb92246d0c34c374703224",
  "db_truth": {
    "attempts": {
      "attempts_distribution": {
        "6": 1,
        "7": 2
      },
      "attempts_max_per_task": 7,
      "attempts_min_per_task": 6,
      "attempts_total": 20,
      "task_count_observed": 3
    },
    "worker_failed_jobs": {
      "max_retry_count": 0,
      "rows": 11
    },
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220",
  "scenario": "S1_PoisonPill",
  "tenant_a": "e20d1cdf-3171-53c7-bbde-ca42fee1c093",
  "tenant_b": "4e8dde8a-f66e-5ac3-8a22-2c9107763cfa",
  "worker_observed": {
    "dlq_rows_observed": 11
  }
}
```

### S2 CrashAfterWritePreAck (N=10)
```json
{
  "N": 10,
  "candidate_sha": "648c89415f3dd1ee6beb92246d0c34c374703224",
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
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220",
  "scenario": "S2_CrashAfterWritePreAck",
  "tenant_a": "e20d1cdf-3171-53c7-bbde-ca42fee1c093",
  "tenant_b": "4e8dde8a-f66e-5ac3-8a22-2c9107763cfa",
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
    "worker_pid_after": 2744,
    "worker_pid_before": 2744,
    "worker_pid_restarts": []
  }
}
```

### S3 RLSProbe (N=1)
```json
{
  "N": 1,
  "candidate_sha": "648c89415f3dd1ee6beb92246d0c34c374703224",
  "db_truth": {
    "pg_connections_error_snapshot": {
      "by_user_state": [
        {
          "count": 9,
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
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220",
  "scenario": "S3_RLSProbe",
  "tenant_a": "e20d1cdf-3171-53c7-bbde-ca42fee1c093",
  "tenant_b": "4e8dde8a-f66e-5ac3-8a22-2c9107763cfa",
  "worker_observed": {
    "error": "TimeoutError: The operation timed out."
  }
}
```

### S4 RunawayNoStarve (sentinels N=10)
```json
{
  "N": 10,
  "candidate_sha": "648c89415f3dd1ee6beb92246d0c34c374703224",
  "db_truth": {
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": false,
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220",
  "scenario": "S4_RunawayNoStarve",
  "tenant_a": "e20d1cdf-3171-53c7-bbde-ca42fee1c093",
  "tenant_b": "4e8dde8a-f66e-5ac3-8a22-2c9107763cfa",
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
  "candidate_sha": "648c89415f3dd1ee6beb92246d0c34c374703224",
  "db_truth": {
    "pg_connections_error_snapshot": {
      "by_user_state": [
        {
          "count": 15,
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
  "run_url": "https://github.com/Muk223/skeldir-2.0/actions/runs/20559855220",
  "scenario": "S5_LeastPrivilege",
  "tenant_a": "e20d1cdf-3171-53c7-bbde-ca42fee1c093",
  "tenant_b": "4e8dde8a-f66e-5ac3-8a22-2c9107763cfa",
  "worker_observed": {
    "error": "TimeoutError: The operation timed out."
  }
}
```

## Where the Evidence Lives

- Workflow: `.github/workflows/r4-worker-failure-semantics.yml`
- Harness: `scripts/r4/worker_failure_semantics.py`
- Summary generator: `scripts/r4/render_r4_summary.py`

