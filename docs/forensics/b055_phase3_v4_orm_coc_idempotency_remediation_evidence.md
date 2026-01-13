# B0.5.5 Phase 3 v4 ORM/CoC/Idempotency Remediation Evidence

## Repo Pin
```
branch: b055-phase3-v4-orm-coc-idempotency
tested_logic_sha: 1ab05359985ed9b743a39203972056186d87b850
current_pr_head_sha: b3acb035c7fb36aac245ab7d0d73a2c05b3187cd
authoritative_ci_run: https://github.com/Muk223/skeldir-2.0/actions/runs/20970090939
status:
(clean)
```

## 3.1 PR Head SHA + CI Run (baseline)
- PR: https://github.com/Muk223/skeldir-2.0/pull/19
- PR head SHA: 1ab05359985ed9b743a39203972056186d87b850
- CI run: https://github.com/Muk223/skeldir-2.0/actions/runs/20969892373

## 3.2 ORM constraint mismatch (baseline)
### Migration unique constraint
File: alembic/versions/004_llm_subsystem/202601131610_add_llm_api_call_idempotency.py
```
op.create_unique_constraint(
    "uq_llm_api_calls_tenant_request_endpoint",
    "llm_api_calls",
    ["tenant_id", "request_id", "endpoint"],
)
```

### ORM model (LLMApiCall __table_args__)
File: backend/app/models/llm.py
```
__table_args__ = (
    CheckConstraint("input_tokens >= 0", name="ck_llm_api_calls_input_tokens_positive"),
    CheckConstraint("output_tokens >= 0", name="ck_llm_api_calls_output_tokens_positive"),
    CheckConstraint("cost_cents >= 0", name="ck_llm_api_calls_cost_cents_positive"),
    CheckConstraint("latency_ms >= 0", name="ck_llm_api_calls_latency_ms_positive"),
)
```

## 3.3 Idempotency + parity coverage (baseline)
### Idempotency tests currently present
File: backend/tests/test_b055_llm_worker_stubs.py
```
async def test_llm_route_idempotency_prevents_duplicate_audit_rows(test_tenant):
    ...
```
No explicit explanation idempotency test present.

### Parity test scope (constraints not checked)
File: backend/tests/test_b055_llm_model_parity.py
```
for col_name, db_col in db_columns.items():
    model_col = model_columns[col_name]
    assert _normalize_type(db_col["type"]) == _normalize_type(model_col.type)
    assert db_col["nullable"] == model_col.nullable
    db_has_default = db_col["default"] is not None
    model_has_default = model_col.server_default is not None
    assert db_has_default == model_has_default
```

## Hypotheses
- H-ORM-1: TRUE (parity test ignores constraints; ORM missing UniqueConstraint)
- H-COC-1: TRUE (evidence not yet pinned to PR head SHA)
- H-IDEMP-1: TRUE (idempotency implemented but no explanation-specific test)

## Remediation (v4)
### ORM constraint parity applied
File: backend/app/models/llm.py
```
__table_args__ = (
    CheckConstraint("input_tokens >= 0", name="ck_llm_api_calls_input_tokens_positive"),
    CheckConstraint("output_tokens >= 0", name="ck_llm_api_calls_output_tokens_positive"),
    CheckConstraint("cost_cents >= 0", name="ck_llm_api_calls_cost_cents_positive"),
    CheckConstraint("latency_ms >= 0", name="ck_llm_api_calls_latency_ms_positive"),
    UniqueConstraint(
        "tenant_id",
        "request_id",
        "endpoint",
        name="uq_llm_api_calls_tenant_request_endpoint",
    ),
)
```

### Explanation idempotency test added
File: backend/tests/test_b055_llm_worker_stubs.py
```
async def test_llm_explanation_idempotency_prevents_duplicate_audit_rows(test_tenant):
    ...
```

## CI evidence (PR head SHA)
- PR: https://github.com/Muk223/skeldir-2.0/pull/19
- PR head SHA: 1ab05359985ed9b743a39203972056186d87b850
- CI run: https://github.com/Muk223/skeldir-2.0/actions/runs/20969892373

### Topology invariants (Test Backend job)
```
Test Backend  Run tests  2026-01-13T19:33:06.0010353Z 
tests/test_b052_queue_topology_and_dlq.py::TestQueueTopology::test_explicit_queues_defined PASSED [ 20%]
Test Backend  Run tests  2026-01-13T19:33:06.0018569Z 
tests/test_b052_queue_topology_and_dlq.py::TestQueueTopology::test_task_routing_rules_defined PASSED [ 40%]
Test Backend  Run tests  2026-01-13T19:33:06.0047768Z 
tests/test_b052_queue_topology_and_dlq.py::TestQueueTopology::test_llm_task_routes_via_router PASSED [ 60%]
Test Backend  Run tests  2026-01-13T19:33:06.0095676Z 
tests/test_b052_queue_topology_and_dlq.py::TestQueueTopology::test_task_names_stable PASSED [ 80%]
Test Backend  Run tests  2026-01-13T19:33:06.1092896Z 
tests/test_b052_queue_topology_and_dlq.py::TestQueueTopology::test_queue_routing_deterministic PASSED [100%]
```

### Idempotency + integrity + parity (Celery Foundation job)
```
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:13.5598963Z 
tests/test_b055_llm_worker_stubs.py::test_llm_stub_atomic_writes_roll_back_on_failure PASSED [ 70%]
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:14.1736192Z 
tests/test_b055_llm_worker_stubs.py::test_llm_stub_rls_blocks_cross_tenant_reads PASSED [ 83%]
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:14.4818599Z 
tests/test_b055_llm_worker_stubs.py::test_llm_explanation_idempotency_prevents_duplicate_audit_rows PASSED [ 90%]
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:14.7860317Z 
tests/test_b055_llm_worker_stubs.py::test_llm_monthly_costs_concurrent_updates_are_atomic PASSED [ 93%]
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:14.9568485Z 
tests/test_b055_llm_worker_stubs.py::test_llm_route_idempotency_prevents_duplicate_audit_rows PASSED [ 96%]
Celery Foundation B0.5.1  Run Celery foundation tests  2026-01-13T19:34:19.0619310Z 
tests/test_b055_llm_model_parity.py::test_llm_models_reflection_parity PASSED [100%]
```
