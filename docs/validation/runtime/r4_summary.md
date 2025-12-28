# R4 Worker Failure Semantics Summary (Truth Anchor)

## Status

R4 = **COMPLETE** as of:

- **Candidate SHA:** `9b154240ab675a1c96b31098addf42f989a16ac6`
- **CI run:** https://github.com/Muk223/skeldir-2.0/actions/runs/20558089099
- **Generated at:** `2025-12-28T18:53:19.492490+00:00`

## Run Configuration (from harness log)

- `broker_url` = `sqla+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `result_backend` = `db+postgresql://app_user:app_user@127.0.0.1:5432/r4`
- `acks_late` = `True`
- `reject_on_worker_lost` = `True`
- `acks_on_failure_or_timeout` = `True`
- `prefetch_multiplier` = `1`
- `tenant_a` = `64fe0d69-359d-5f87-8b72-ac02e87a048a`
- `tenant_b` = `ba161e06-dbb4-5dc1-bda5-92796a847bd8`

## Exit Gates (Pass Matrix)

| Gate | Description | Status |
|------|-------------|--------|
| EG-R4-0 | Instrument & SHA binding | PASS |
| EG-R4-1 | Retry/DLQ physics (PoisonPill N=10) | PASS |
| EG-R4-2 | Idempotency under crash (CrashAfterWritePreAck N=10) | PASS |
| EG-R4-3 | Worker RLS enforcement (Cross-tenant probe) | PASS |
| EG-R4-4 | Timeouts & starvation resistance (Runaway + sentinels) | PASS |
| EG-R4-5 | Least privilege reality (probes fail) | PASS |
| EG-R4-6 | Evidence pack present (verdict blocks S1..S5) | PASS |

## Evidence (Browser-Verifiable Logs)

This run prints, to CI logs, one `R4_VERDICT_BEGIN/END` JSON block per scenario.

Log step containing verdict blocks: `Run R4 harness` in `.github/workflows/r4-worker-failure-semantics.yml`.

## Key Verdicts

### S1 PoisonPill (N=10)
```json
{
  "N": 10,
  "db_truth": {
    "worker_failed_jobs": {
      "max_retry_count": 3,
      "rows": 10
    },
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 0
    }
  },
  "passed": true,
  "scenario": "S1_PoisonPill",
  "tenant_a": "64fe0d69-359d-5f87-8b72-ac02e87a048a",
  "tenant_b": "ba161e06-dbb4-5dc1-bda5-92796a847bd8",
  "worker_observed": {
    "failed_results": 10,
    "successful_results": 0
  }
}
```

### S2 CrashAfterWritePreAck (N=10)
```json
{
  "N": 10,
  "db_truth": {
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 10
    }
  },
  "passed": true,
  "scenario": "S2_CrashAfterWritePreAck",
  "tenant_a": "64fe0d69-359d-5f87-8b72-ac02e87a048a",
  "tenant_b": "ba161e06-dbb4-5dc1-bda5-92796a847bd8",
  "worker_observed": {
    "failed_results": 0,
    "successful_results": 10
  }
}
```

### S3 RLSProbe (N=1)
```json
{
  "N": 1,
  "db_truth": {
    "missing_tenant_dlq_rows": 1
  },
  "passed": true,
  "scenario": "S3_RLSProbe",
  "tenant_a": "64fe0d69-359d-5f87-8b72-ac02e87a048a",
  "tenant_b": "ba161e06-dbb4-5dc1-bda5-92796a847bd8",
  "worker_observed": {
    "bad_failed": true,
    "visible_count_for_tenant_a": 0
  }
}
```

### S4 RunawayNoStarve (sentinels N=10)
```json
{
  "N": 10,
  "db_truth": {
    "worker_side_effects": {
      "duplicate_task_ids": 0,
      "rows": 10
    }
  },
  "passed": true,
  "scenario": "S4_RunawayNoStarve",
  "tenant_a": "64fe0d69-359d-5f87-8b72-ac02e87a048a",
  "tenant_b": "ba161e06-dbb4-5dc1-bda5-92796a847bd8",
  "worker_observed": {
    "runaway_outcome": "SoftTimeLimitExceeded",
    "sentinel_success": 10
  }
}
```

### S5 LeastPrivilege (N=1)
```json
{
  "N": 1,
  "db_truth": {
    "worker_failed_jobs_rows": 0
  },
  "passed": true,
  "scenario": "S5_LeastPrivilege",
  "tenant_a": "64fe0d69-359d-5f87-8b72-ac02e87a048a",
  "tenant_b": "ba161e06-dbb4-5dc1-bda5-92796a847bd8",
  "worker_observed": {
    "probe_results": {
      "bypass_rls_attempt": {
        "error": "query would be affected by row-level security policy for table \"attribution_events\"\n",
        "ok": "false"
      },
      "create_role": {
        "error": "permission denied to create role\nDETAIL:  Only roles with the CREATEROLE attribute may create roles.\n",
        "ok": "false"
      },
      "ddl_create_table": {
        "error": "permission denied for schema public\nLINE 1: CREATE TABLE r4_priv_probe_tmp(id INT)\n                     ^\n",
        "ok": "false"
      },
      "disable_rls": {
        "error": "must be owner of table attribution_events\n",
        "ok": "false"
      },
      "force_rls": {
        "error": "must be owner of table attribution_events\n",
        "ok": "false"
      },
      "grant_admin_role": {
        "error": "permission denied to grant role \"pg_read_all_data\"\nDETAIL:  Only roles with the ADMIN option on role \"pg_read_all_data\" may grant this role.\n",
        "ok": "false"
      },
      "set_bypassrls": {
        "error": "permission denied to alter role\nDETAIL:  Only roles with the CREATEROLE attribute and the ADMIN option on role \"app_user\" may alter this role.\n",
        "ok": "false"
      }
    },
    "required_failures": {
      "bypass_rls_attempt": true,
      "create_role": true,
      "ddl_create_table": true,
      "disable_rls": true,
      "force_rls": true,
      "grant_admin_role": true,
      "set_bypassrls": true
    }
  }
}
```

## Where the Evidence Lives

- Workflow: `.github/workflows/r4-worker-failure-semantics.yml`
- Harness: `scripts/r4/worker_failure_semantics.py`
- Summary generator: `scripts/r4/render_r4_summary.py`

