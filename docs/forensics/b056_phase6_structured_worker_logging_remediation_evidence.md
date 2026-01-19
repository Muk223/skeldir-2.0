# B0.5.6 Phase 6: Structured Worker Logging Remediation Evidence

**Date**: 2026-01-19
**Investigator**: Codex (automated remediation execution)
**Phase**: B0.5.6.6 ? Context-Robust Hypothesis-Driven Remediation
**Status**: COMPLETE (local runtime proof + test; CI URL pending)

---

## 0. Non-negotiable intent (acceptance authority)

- Metrics remain bounded: no `tenant_id` in Prometheus labels.
- Tenant traceability exists for incident response: `tenant_id` and `correlation_id` are emitted in structured worker logs (stdout/stderr), not metrics labels.
- Phase is complete only with real worker runtime output proving a stable lifecycle schema for **success** and **failure**.

## 1. Hypotheses (validated/refuted)

### H-BLOCK-1 (missing runtime proof) ? VALIDATED ? RESOLVED
- Before: no canonical lifecycle records; see ?3.1 baseline output.
- After: canonical lifecycle records present; see ?3.2 + subprocess test in ?5.

### H-BLOCK-2 (logging configured but not correct) ? VALIDATED ? RESOLVED
- Worker logs were JSON, but lifecycle schema keys were missing/misaligned (e.g., `correlation_id_request` not `correlation_id`) and extra fields were dropped by formatter allowlist.

### H-BLOCK-3 (context propagation exists but not injected) ? VALIDATED ? RESOLVED
- `extra={...}` fields were not reliably surfaced in JSON output due to formatter behavior.
- Fix uses a dedicated raw-JSON lifecycle logger + deterministic context extraction.

### H-BLOCK-4 (Celery logging interference) ? PARTIAL (contained)
- Celery emits its own logs; some include unbounded tracebacks (e.g., `celery.app.trace`).
- Fix does not attempt to change Celery trace logging; it ensures lifecycle logs are isolated, stable JSON with allowlisted keys.

### H-BLOCK-5 (PII spill risk) ? MITIGATED for lifecycle logs
- Lifecycle logs are allowlisted (closed set) and tests assert forbidden fields are absent.

### Root-cause hypotheses summary
- H-RC-1 (init gap): **REFUTED** ? worker process init already calls `configure_logging()`. 
- H-RC-3 (no canonical schema emitter): **VALIDATED** ? no universal start/success/failure schema logger existed.
- H-RC-4 (context extraction fragile): **VALIDATED** ? context keys and extras were inconsistent/dropped.
- H-RC-6 (tests are lying): **VALIDATED** ? prior log assertions used eager/caplog patterns; new subprocess test added.

---

## 2. Mandatory investigation ? static mapping (verbatim rg outputs)

### 2.1 Find logging stack + init points

Command:
```powershell
rg -n "structlog|pythonjsonlogger|jsonlogger|logging\.config|dictConfig|basicConfig" backend/app
```

Output:
```text
﻿backend/app\observability\logging_config.py:46:    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), handlers=[handler], force=True)
backend/app\ingestion\dlq_handler.py:22:    import structlog
backend/app\ingestion\dlq_handler.py:23:    logger = structlog.get_logger(__name__)
```

### 2.2 Find init points

Command:
```powershell
rg -n "init_logging|configure_logging|logging\.getLogger\(" backend/app
```

Output:
```text
﻿backend/app\celery_app.py:28:from app.observability.logging_config import configure_logging
backend/app\celery_app.py:33:logger = logging.getLogger(__name__)
backend/app\celery_app.py:269:    configure_logging(settings.LOG_LEVEL)
backend/app\api\health.py:27:logger = logging.getLogger(__name__)
backend/app\workers\llm.py:28:logger = logging.getLogger(__name__)
backend/app\services\revenue_reconciliation.py:33:logger = logging.getLogger(__name__)
backend/app\tasks\context.py:21:logger = logging.getLogger(__name__)
backend/app\llm\budget_policy.py:35:logger = logging.getLogger(__name__)
backend/app\tasks\attribution.py:28:logger = logging.getLogger(__name__)
backend/app\services\investigation.py:32:logger = logging.getLogger(__name__)
backend/app\tasks\housekeeping.py:24:logger = logging.getLogger(__name__)
backend/app\tasks\llm.py:25:logger = logging.getLogger(__name__)
backend/app\tasks\maintenance.py:26:logger = logging.getLogger(__name__)
backend/app\tasks\health.py:19:logger = logging.getLogger(__name__)
backend/app\tasks\matviews.py:22:logger = logging.getLogger(__name__)
backend/app\tasks\r4_failure_semantics.py:24:logger = logging.getLogger(__name__)
backend/app\ingestion\channel_normalization.py:24:logger = logging.getLogger(__name__)
backend/app\tasks\r6_resource_governance.py:18:logger = logging.getLogger(__name__)
backend/app\ingestion\event_service.py:32:logger = logging.getLogger(__name__)
backend/app\matviews\executor.py:26:logger = logging.getLogger(__name__)
backend/app\ingestion\dlq_handler.py:26:    logger = logging.getLogger(__name__)
backend/app\core\pg_locks.py:17:logger = logging.getLogger(__name__)
backend/app\core\tenant_context.py:26:logger = logging.getLogger(__name__)
backend/app\middleware\pii_stripping.py:35:logger = logging.getLogger(__name__)
backend/app\observability\logging_config.py:43:def configure_logging(level: str = "INFO") -> None:
```

### 2.3 Find Celery entry + lifecycle hooks

Command:
```powershell
rg -n "Celery\(|celery_app|@signals\.|task_(pre|post)run|task_failure|after_setup_logger|after_setup_task_logger" backend/app
```

Output:
```text
﻿backend/app\celery_app.py:110:celery_app = Celery("skeldir_backend")
backend/app\celery_app.py:145:    celery_app.conf.update(
backend/app\celery_app.py:214:    celery_app.control_cls = "app.celery_control:SkeldirControl"
backend/app\celery_app.py:218:    celery_app.conf.beat_schedule = BEAT_SCHEDULE
backend/app\celery_app.py:221:        "celery_app_configured",
backend/app\celery_app.py:223:            "broker_url": celery_app.conf.broker_url,
backend/app\celery_app.py:224:            "result_backend": celery_app.conf.result_backend,
backend/app\celery_app.py:225:            "broker_transport_options": celery_app.conf.broker_transport_options,
backend/app\celery_app.py:226:            "queues": [q.name for q in celery_app.conf.task_queues],
backend/app\celery_app.py:227:            "beat_schedule_loaded": bool(celery_app.conf.beat_schedule),
backend/app\celery_app.py:228:            "scheduled_tasks": list(celery_app.conf.beat_schedule.keys()) if celery_app.conf.beat_schedule else [],
backend/app\celery_app.py:229:            "app_name": celery_app.main,
backend/app\celery_app.py:235:@signals.worker_init.connect
backend/app\celery_app.py:257:@signals.worker_process_init.connect
backend/app\celery_app.py:273:@signals.worker_process_shutdown.connect
backend/app\celery_app.py:343:    if not str(celery_app.conf.broker_url or "").startswith("sqla+"):
backend/app\celery_app.py:491:    tasks = sorted(celery_app.tasks.keys())
backend/app\celery_app.py:504:@signals.worker_ready.connect
backend/app\celery_app.py:513:@signals.task_prerun.connect
backend/app\celery_app.py:514:def _on_task_prerun(task_id, task, **kwargs):
backend/app\celery_app.py:523:@signals.task_postrun.connect
backend/app\celery_app.py:524:def _on_task_postrun(task_id, task, retval, state, **kwargs):
backend/app\celery_app.py:539:@signals.task_failure.connect
backend/app\celery_app.py:540:def _on_task_failure(task_id=None, exception=None, args=None, kwargs=None, einfo=None, **extra):
backend/app\celery_app.py:549:    metrics_module.celery_task_failure_total.labels(task_name=normalized_name).inc()
backend/app\celery_app.py:796:__all__ = ["celery_app", "_build_broker_url", "_build_result_backend", "_ensure_celery_configured"]
backend/app\celery_app.py:800:# Module-level imports caused: conftest ΓåÆ celery_app ΓåÆ tasks.housekeeping ΓåÆ psycopg2 ΓåÆ DB connection
backend/app\observability\metrics.py:75:celery_task_failure_total = Counter(
backend/app\observability\metrics.py:76:    "celery_task_failure_total",
backend/app\observability\metrics_policy.py:79:# Derived from app/tasks/*.py @celery_app.task(name=...) definitions.
backend/app\api\health.py:24:from app.celery_app import celery_app
backend/app\api\health.py:82:        task_result = celery_app.send_task(
backend/app\tasks\housekeeping.py:19:from app.celery_app import celery_app
backend/app\tasks\housekeeping.py:99:@celery_app.task(bind=True, name="app.tasks.housekeeping.ping", routing_key="housekeeping.task")
backend/app\tasks\maintenance.py:19:from app.celery_app import celery_app
backend/app\tasks\maintenance.py:66:@celery_app.task(
backend/app\tasks\maintenance.py:106:@celery_app.task(
backend/app\tasks\maintenance.py:178:@celery_app.task(
backend/app\tasks\maintenance.py:241:@celery_app.task(
backend/app\tasks\health.py:15:from app.celery_app import celery_app
backend/app\tasks\health.py:47:@celery_app.task(bind=True, name="app.tasks.health.probe", routing_key="housekeeping.task")
backend/app\tasks\llm.py:13:from app.celery_app import celery_app
backend/app\tasks\llm.py:74:@celery_app.task(
backend/app\tasks\llm.py:131:@celery_app.task(bind=True, name="app.tasks.llm.explanation", max_retries=3, default_retry_delay=30)
backend/app\tasks\llm.py:186:@celery_app.task(bind=True, name="app.tasks.llm.investigation", max_retries=3, default_retry_delay=30)
backend/app\tasks\llm.py:241:@celery_app.task(bind=True, name="app.tasks.llm.budget_optimization", max_retries=3, default_retry_delay=30)
backend/app\tasks\r6_resource_governance.py:16:from app.celery_app import celery_app
backend/app\tasks\r6_resource_governance.py:70:@celery_app.task(
backend/app\tasks\r6_resource_governance.py:120:@celery_app.task(
backend/app\tasks\r6_resource_governance.py:163:@celery_app.task(
backend/app\tasks\r6_resource_governance.py:191:@celery_app.task(
backend/app\tasks\r6_resource_governance.py:229:@celery_app.task(
backend/app\tasks\r6_resource_governance.py:267:@celery_app.task(
backend/app\tasks\matviews.py:16:from app.celery_app import celery_app
backend/app\tasks\matviews.py:217:@celery_app.task(
backend/app\tasks\matviews.py:268:@celery_app.task(
backend/app\tasks\matviews.py:343:@celery_app.task(
backend/app\tasks\attribution.py:22:from app.celery_app import celery_app
backend/app\tasks\attribution.py:490:@celery_app.task(
backend/app\tasks\r4_failure_semantics.py:21:from app.celery_app import _sync_sqlalchemy_url, celery_app
backend/app\tasks\r4_failure_semantics.py:106:@celery_app.task(
backend/app\tasks\r4_failure_semantics.py:162:@celery_app.task(
backend/app\tasks\r4_failure_semantics.py:255:@celery_app.task(bind=True, name="app.tasks.r4_failure_semantics.rls_cross_tenant_probe", acks_late=False)
backend/app\tasks\r4_failure_semantics.py:294:@celery_app.task(
backend/app\tasks\r4_failure_semantics.py:328:@celery_app.task(bind=True, name="app.tasks.r4_failure_semantics.sentinel_side_effect", acks_late=False)
backend/app\tasks\r4_failure_semantics.py:350:@celery_app.task(bind=True, name="app.tasks.r4_failure_semantics.privilege_probes", acks_late=False)
backend/app\core\queues.py:8:# Core queue definitions (must match celery_app.py task_queues)
```

### 2.4 Find tenant/correlation context sources

Command:
```powershell
rg -n "tenant_id|correlation_id|set_tenant|set_.*correlation|request\.correlation" backend/app
```

Output:
```text
﻿backend/app\celery_app.py:658:        tenant_id = None
backend/app\celery_app.py:659:        if kwargs and 'tenant_id' in kwargs:
backend/app\celery_app.py:661:                tenant_id = UUID(str(kwargs['tenant_id']))
backend/app\celery_app.py:679:        correlation_id = None
backend/app\celery_app.py:684:            correlation_id_val = getattr(task.request, 'correlation_id', None)
backend/app\celery_app.py:685:            if correlation_id_val:
backend/app\celery_app.py:687:                    correlation_id = UUID(str(correlation_id_val))
backend/app\celery_app.py:694:        if correlation_id is None and kwargs and "correlation_id" in kwargs:
backend/app\celery_app.py:696:                correlation_id = UUID(str(kwargs["correlation_id"]))
backend/app\celery_app.py:698:                correlation_id = None
backend/app\celery_app.py:700:        if correlation_id is None and task_id:
backend/app\celery_app.py:702:                correlation_id = UUID(str(task_id))
backend/app\celery_app.py:704:                correlation_id = None
backend/app\celery_app.py:730:            if tenant_id:
backend/app\celery_app.py:732:                    "SELECT set_config('app.current_tenant_id', %s, true);",
backend/app\celery_app.py:733:                    (str(tenant_id),),
backend/app\celery_app.py:735:            if correlation_id:
backend/app\celery_app.py:737:                    "SELECT set_config('app.correlation_id', %s, true);",
backend/app\celery_app.py:738:                    (str(correlation_id),),
backend/app\celery_app.py:750:                    task_args, task_kwargs, tenant_id,
backend/app\celery_app.py:752:                    retry_count, status, correlation_id, failed_at
backend/app\celery_app.py:767:                str(tenant_id) if tenant_id else None,
backend/app\celery_app.py:774:                str(correlation_id) if correlation_id else None,
backend/app\api\webhooks.py:31:    set_tenant_id,
backend/app\api\webhooks.py:32:    set_business_correlation_id,
backend/app\api\webhooks.py:33:    get_request_correlation_id,
backend/app\api\webhooks.py:67:    set_tenant_id(tenant_info["tenant_id"])
backend/app\api\webhooks.py:85:    tenant_id,
backend/app\api\webhooks.py:87:    correlation_id: str,
backend/app\api\webhooks.py:92:    async with get_session(tenant_id=tenant_id) as session:
backend/app\api\webhooks.py:102:            tenant_id=tenant_id,
backend/app\api\webhooks.py:105:            correlation_id=correlation_id,
backend/app\api\webhooks.py:111:async def _handle_ingestion(tenant_id, event_data: dict, idempotency_key: str, source: str):
backend/app\api\webhooks.py:115:        tenant_id=tenant_id,
backend/app\api\webhooks.py:128:    # Validation errors routed to DLQ: locate the dead_event using correlation_id
backend/app\api\webhooks.py:129:    correlation_id = _make_correlation_uuid(idempotency_key)
backend/app\api\webhooks.py:130:    async with get_session(tenant_id=tenant_id) as session:
backend/app\api\webhooks.py:133:            select(DeadEvent).where(DeadEvent.correlation_id == correlation_id)
backend/app\api\webhooks.py:171:    set_business_correlation_id(idempotency_key)
backend/app\api\webhooks.py:181:        "correlation_id": str(_make_correlation_uuid(idempotency_key)),
backend/app\api\webhooks.py:183:    return await _handle_ingestion(tenant_info["tenant_id"], event_data, idempotency_key, source="shopify")
backend/app\api\webhooks.py:209:    set_business_correlation_id(idempotency_key)
backend/app\api\webhooks.py:224:        "correlation_id": str(_make_correlation_uuid(idempotency_key)),
backend/app\api\webhooks.py:226:    return await _handle_ingestion(tenant_info["tenant_id"], event_data, idempotency_key, source="stripe")
backend/app\api\webhooks.py:282:    set_business_correlation_id(idempotency_key)
backend/app\api\webhooks.py:288:            tenant_id=tenant_info["tenant_id"],
backend/app\api\webhooks.py:290:            correlation_id=correlation_uuid,
backend/app\api\webhooks.py:295:                "correlation_id": correlation_uuid,
backend/app\api\webhooks.py:320:            tenant_id=tenant_info["tenant_id"],
backend/app\api\webhooks.py:322:            correlation_id=correlation_uuid,
backend/app\api\webhooks.py:327:                "correlation_id": correlation_uuid,
backend/app\api\webhooks.py:350:        "correlation_id": correlation_uuid,
backend/app\api\webhooks.py:355:        tenant_id=tenant_info["tenant_id"],
backend/app\api\webhooks.py:369:    # Validation errors routed to DLQ by service: locate via correlation_id for response
backend/app\api\webhooks.py:370:    async with get_session(tenant_id=tenant_info["tenant_id"]) as session:
backend/app\api\webhooks.py:373:            select(DeadEvent).where(DeadEvent.correlation_id == uuid5(NAMESPACE_URL, idempotency_key))
backend/app\api\webhooks.py:406:    set_business_correlation_id(idempotency_key)
backend/app\api\webhooks.py:417:        "correlation_id": str(_make_correlation_uuid(idempotency_key)),
backend/app\api\webhooks.py:419:    return await _handle_ingestion(tenant_info["tenant_id"], event_data, idempotency_key, source="paypal")
backend/app\api\webhooks.py:444:    set_business_correlation_id(idempotency_key)
backend/app\api\webhooks.py:455:        "correlation_id": str(_make_correlation_uuid(idempotency_key)),
backend/app\api\webhooks.py:457:    return await _handle_ingestion(tenant_info["tenant_id"], event_data, idempotency_key, source="woocommerce")
backend/app\api\health.py:247:                text("SELECT set_config('app.current_tenant_id', :tid, false)"),
backend/app\api\health.py:251:                text("SELECT current_setting('app.current_tenant_id', true)")
backend/app\api\attribution.py:32:    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")]
backend/app\api\attribution.py:55:    tenant_id = os.getenv('TEST_TENANT_ID', '00000000-0000-0000-0000-000000000000')
backend/app\api\attribution.py:67:        "tenant_id": tenant_id,
backend/app\core\tenant_context.py:42:        dict with keys: tenant_id (UUID), shopify_webhook_secret, stripe_webhook_secret,
backend/app\core\tenant_context.py:57:                  id AS tenant_id,
backend/app\core\tenant_context.py:75:        "tenant_id": UUID(str(row["tenant_id"])),
backend/app\core\tenant_context.py:83:def derive_tenant_id_from_request(request: Request) -> Optional[UUID]:
backend/app\core\tenant_context.py:85:    Canonical algorithm for deriving tenant_id from API requests.
backend/app\core\tenant_context.py:88:    1. JWT claims: `request.state.auth_context.tenant_id` (set by B1.2 Auth middleware)
backend/app\core\tenant_context.py:98:        TenantContextError: If tenant_id is required but cannot be derived
backend/app\core\tenant_context.py:101:    if hasattr(request.state, 'auth_context') and hasattr(request.state.auth_context, 'tenant_id'):
backend/app\core\tenant_context.py:102:        tenant_id = request.state.auth_context.tenant_id
backend/app\core\tenant_context.py:103:        if tenant_id:
backend/app\core\tenant_context.py:106:                extra={"tenant_id": str(tenant_id), "source": "jwt"}
backend/app\core\tenant_context.py:108:            return UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
backend/app\core\tenant_context.py:124:async def set_tenant_context_on_session(
backend/app\core\tenant_context.py:126:    tenant_id: UUID,
backend/app\core\tenant_context.py:132:    This function executes `SET LOCAL app.current_tenant_id = :tenant_id` (or `SET app.current_tenant_id`)
backend/app\core\tenant_context.py:137:        tenant_id: Tenant UUID to set as context
backend/app\core\tenant_context.py:143:    command = "SET LOCAL app.current_tenant_id" if local else "SET app.current_tenant_id"
backend/app\core\tenant_context.py:145:        text(f"{command} = :tenant_id"),
backend/app\core\tenant_context.py:146:        {"tenant_id": str(tenant_id)}
backend/app\core\tenant_context.py:150:        extra={"tenant_id": str(tenant_id), "scope": "local" if local else "session"}
backend/app\core\tenant_context.py:174:    1. Derives tenant_id from request (JWT or API key)
backend/app\core\tenant_context.py:175:    2. Sets `app.current_tenant_id` on the database session
backend/app\core\tenant_context.py:191:    # Derive tenant_id from request
backend/app\core\tenant_context.py:192:    tenant_id = derive_tenant_id_from_request(request)
backend/app\core\tenant_context.py:194:    if not tenant_id:
backend/app\core\tenant_context.py:212:            extra={"tenant_id": str(tenant_id)}
backend/app\core\tenant_context.py:223:        await set_tenant_context_on_session(session, tenant_id, local=True)
backend/app\core\tenant_context.py:233:            extra={"tenant_id": str(tenant_id), "error": str(e)},
backend/app\core\pg_locks.py:46:def build_refresh_lock_key(view_name: str, tenant_id: Optional[UUID]) -> RefreshLockKey:
backend/app\core\pg_locks.py:50:    Keys are derived separately from view_name and tenant_id to reduce
backend/app\core\pg_locks.py:53:    tenant_token = str(tenant_id) if tenant_id else "GLOBAL"
backend/app\core\pg_locks.py:67:    tenant_id: Optional[UUID] = None,
backend/app\core\pg_locks.py:75:    lock_key = build_refresh_lock_key(view_name, tenant_id)
backend/app\workers\llm.py:35:        "tenant_id": str(model.tenant_id),
backend/app\workers\llm.py:37:        "correlation_id": model.correlation_id,
backend/app\workers\llm.py:48:    if model.correlation_id:
backend/app\workers\llm.py:49:        return model.correlation_id
backend/app\workers\llm.py:53:def _resolve_correlation_id(model: LLMTaskPayload, endpoint: str) -> str:
backend/app\workers\llm.py:54:    if model.correlation_id:
backend/app\workers\llm.py:55:        return model.correlation_id
backend/app\workers\llm.py:58:    return _stable_fallback_id(model, endpoint, "correlation_id")
backend/app\workers\llm.py:75:    correlation_id: str,
backend/app\workers\llm.py:80:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:92:                "correlation_id": correlation_id,
backend/app\workers\llm.py:96:            index_elements=["tenant_id", "request_id", "endpoint"]
backend/app\workers\llm.py:109:                LLMApiCall.tenant_id == model.tenant_id,
backend/app\workers\llm.py:149:    tenant_id: UUID,
backend/app\workers\llm.py:159:            tenant_id=tenant_id,
backend/app\workers\llm.py:168:        index_elements=["tenant_id", "month"],
backend/app\workers\llm.py:189:    correlation_id = _resolve_correlation_id(model, "app.tasks.llm.route")
backend/app\workers\llm.py:196:            correlation_id=correlation_id,
backend/app\workers\llm.py:203:                "correlation_id": correlation_id,
backend/app\workers\llm.py:210:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:220:            "tenant_id": str(model.tenant_id),
backend/app\workers\llm.py:221:            "correlation_id": correlation_id,
backend/app\workers\llm.py:231:        "correlation_id": correlation_id,
backend/app\workers\llm.py:243:    correlation_id = _resolve_correlation_id(model, "app.tasks.llm.explanation")
backend/app\workers\llm.py:250:            correlation_id=correlation_id,
backend/app\workers\llm.py:257:                "correlation_id": correlation_id,
backend/app\workers\llm.py:264:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:274:            "tenant_id": str(model.tenant_id),
backend/app\workers\llm.py:275:            "correlation_id": correlation_id,
backend/app\workers\llm.py:285:        "correlation_id": correlation_id,
backend/app\workers\llm.py:297:    correlation_id = _resolve_correlation_id(model, "app.tasks.llm.investigation")
backend/app\workers\llm.py:304:            correlation_id=correlation_id,
backend/app\workers\llm.py:310:                        Investigation.tenant_id == model.tenant_id,
backend/app\workers\llm.py:319:                "correlation_id": correlation_id,
backend/app\workers\llm.py:326:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:336:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:346:            "tenant_id": str(model.tenant_id),
backend/app\workers\llm.py:347:            "correlation_id": correlation_id,
backend/app\workers\llm.py:357:        "correlation_id": correlation_id,
backend/app\workers\llm.py:370:    correlation_id = _resolve_correlation_id(model, "app.tasks.llm.budget_optimization")
backend/app\workers\llm.py:377:            correlation_id=correlation_id,
backend/app\workers\llm.py:383:                        BudgetOptimizationJob.tenant_id == model.tenant_id,
backend/app\workers\llm.py:392:                "correlation_id": correlation_id,
backend/app\workers\llm.py:399:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:408:            tenant_id=model.tenant_id,
backend/app\workers\llm.py:418:            "tenant_id": str(model.tenant_id),
backend/app\workers\llm.py:419:            "correlation_id": correlation_id,
backend/app\workers\llm.py:429:        "correlation_id": correlation_id,
backend/app\core\channel_service.py:37:    """Raised when tenant_id doesn't match entity's tenant."""
backend/app\core\channel_service.py:169:    tenant_id: UUID,
backend/app\core\channel_service.py:186:        tenant_id: Tenant owning the entity
backend/app\core\channel_service.py:192:        PermissionError: If tenant_id doesn't match entity's tenant
backend/app\core\channel_service.py:196:        2. Validates entity exists and belongs to tenant_id
backend/app\core\channel_service.py:231:            text("SELECT tenant_id, channel_code FROM attribution_allocations WHERE id = :id"),
backend/app\core\channel_service.py:236:            text("SELECT tenant_id, channel FROM attribution_events WHERE id = :id"),
backend/app\core\channel_service.py:243:    entity_tenant_id, current_channel = entity_result
backend/app\core\channel_service.py:245:    if UUID(str(entity_tenant_id)) != tenant_id:
backend/app\core\channel_service.py:247:            f"Entity belongs to tenant '{entity_tenant_id}', not '{tenant_id}'"
backend/app\core\channel_service.py:257:        text("SET LOCAL app.current_tenant_id = :tenant_id"),
backend/app\core\channel_service.py:258:        {"tenant_id": str(tenant_id)}
backend/app\core\channel_service.py:284:                        tenant_id, entity_type, entity_id,
backend/app\core\channel_service.py:287:                        :tenant_id, 'event', :entity_id,
backend/app\core\channel_service.py:293:                    "tenant_id": str(tenant_id),
backend/app\core\channel_service.py:308:        session.execute(text("RESET app.current_tenant_id"))
backend/app\api\auth.py:41:    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")]
backend/app\api\auth.py:80:    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")]
backend/app\api\auth.py:111:    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")]
backend/app\matviews\executor.py:23:from app.db.session import engine, set_tenant_guc
backend/app\matviews\executor.py:40:    tenant_id: Optional[UUID]
backend/app\matviews\executor.py:41:    correlation_id: Optional[str]
backend/app\matviews\executor.py:52:            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
backend/app\matviews\executor.py:53:            "correlation_id": self.correlation_id,
backend/app\matviews\executor.py:118:    tenant_id: Optional[UUID],
backend/app\matviews\executor.py:119:    correlation_id: Optional[str] = None,
backend/app\matviews\executor.py:131:            if tenant_id:
backend/app\matviews\executor.py:132:                await set_tenant_guc(conn, tenant_id, local=True)
backend/app\matviews\executor.py:134:            acquired, lock_key = await try_acquire_refresh_xact_lock(conn, view_name, tenant_id)
backend/app\matviews\executor.py:138:                    tenant_id=tenant_id,
backend/app\matviews\executor.py:139:                    correlation_id=correlation_id,
backend/app\matviews\executor.py:161:            tenant_id=tenant_id,
backend/app\matviews\executor.py:162:            correlation_id=correlation_id,
backend/app\matviews\executor.py:177:                "tenant_id": str(tenant_id) if tenant_id else None,
backend/app\matviews\executor.py:178:                "correlation_id": correlation_id,
backend/app\matviews\executor.py:183:            tenant_id=tenant_id,
backend/app\matviews\executor.py:184:            correlation_id=correlation_id,
backend/app\matviews\executor.py:196:    tenant_id: Optional[UUID],
backend/app\matviews\executor.py:197:    correlation_id: Optional[str] = None,
backend/app\matviews\executor.py:214:            if tenant_id:
backend/app\matviews\executor.py:216:                    "SELECT set_config('app.current_tenant_id', %s, true)",
backend/app\matviews\executor.py:217:                    (str(tenant_id),),
backend/app\matviews\executor.py:223:            lock_key = build_refresh_lock_key(view_name, tenant_id)
backend/app\matviews\executor.py:233:                    tenant_id=tenant_id,
backend/app\matviews\executor.py:234:                    correlation_id=correlation_id,
backend/app\matviews\executor.py:260:            tenant_id=tenant_id,
backend/app\matviews\executor.py:261:            correlation_id=correlation_id,
backend/app\matviews\executor.py:276:                "tenant_id": str(tenant_id) if tenant_id else None,
backend/app\matviews\executor.py:277:                "correlation_id": correlation_id,
backend/app\matviews\executor.py:282:            tenant_id=tenant_id,
backend/app\matviews\executor.py:283:            correlation_id=correlation_id,
backend/app\matviews\executor.py:294:    tenant_id: UUID,
backend/app\matviews\executor.py:295:    correlation_id: Optional[str] = None,
backend/app\matviews\executor.py:300:        results.append(await refresh_single_async(entry.name, tenant_id, correlation_id))
backend/app\matviews\executor.py:305:    tenant_id: UUID,
backend/app\matviews\executor.py:306:    correlation_id: Optional[str] = None,
backend/app\matviews\executor.py:314:        results.append(refresh_single(entry.name, tenant_id, correlation_id))
backend/app\services\investigation.py:86:    tenant_id: UUID
backend/app\services\investigation.py:136:        tenant_id: UUID,
backend/app\services\investigation.py:137:        correlation_id: Optional[str] = None,
backend/app\services\investigation.py:147:            tenant_id: Tenant UUID.
backend/app\services\investigation.py:148:            correlation_id: Optional correlation ID for tracing.
backend/app\services\investigation.py:162:                    id, tenant_id, correlation_id, status,
backend/app\services\investigation.py:165:                    :id, :tenant_id, :correlation_id, 'PENDING',
backend/app\services\investigation.py:171:                "tenant_id": str(tenant_id),
backend/app\services\investigation.py:172:                "correlation_id": correlation_id,
backend/app\services\investigation.py:183:                "tenant_id": str(tenant_id),
backend/app\services\investigation.py:190:            tenant_id=tenant_id,
backend/app\services\investigation.py:204:        tenant_id: UUID,
backend/app\services\investigation.py:215:            tenant_id: Tenant UUID.
backend/app\services\investigation.py:226:                    id, tenant_id, status, created_at, min_hold_until,
backend/app\services\investigation.py:229:                WHERE id = :job_id AND tenant_id = :tenant_id
backend/app\services\investigation.py:231:            {"job_id": str(job_id), "tenant_id": str(tenant_id)},
backend/app\services\investigation.py:256:            tenant_id=UUID(str(row["tenant_id"])),
backend/app\services\investigation.py:291:        tenant_id: UUID,
backend/app\services\investigation.py:302:            tenant_id: Tenant UUID.
backend/app\services\investigation.py:312:        job = await self.get_job(conn, tenant_id, job_id)
backend/app\services\investigation.py:333:                WHERE id = :job_id AND tenant_id = :tenant_id
backend/app\services\investigation.py:337:                "tenant_id": str(tenant_id),
backend/app\services\investigation.py:345:            extra={"job_id": str(job_id), "tenant_id": str(tenant_id)},
backend/app\services\investigation.py:350:            tenant_id=job.tenant_id,
backend/app\services\attribution.py:40:    tenant_id: UUID,
backend/app\services\attribution.py:43:    correlation_id: Optional[str] = None,
backend/app\services\attribution.py:51:    correlation_id, and propagates that correlation into both task kwargs and
backend/app\services\attribution.py:60:    correlation_uuid = UUID(str(correlation_id)) if correlation_id else uuid4()
backend/app\services\attribution.py:66:            "tenant_id": tenant_id,
backend/app\services\attribution.py:69:            "correlation_id": str(correlation_uuid),
backend/app\services\attribution.py:73:        correlation_id=str(correlation_uuid),
backend/app\llm\budget_policy.py:264:        tenant_id: UUID,
backend/app\llm\budget_policy.py:268:        correlation_id: Optional[str] = None,
backend/app\llm\budget_policy.py:277:            tenant_id: Tenant UUID for RLS.
backend/app\llm\budget_policy.py:281:            correlation_id: Optional correlation ID.
backend/app\llm\budget_policy.py:295:            tenant_id=tenant_id,
backend/app\llm\budget_policy.py:300:            correlation_id=correlation_id,
backend/app\llm\budget_policy.py:306:                "tenant_id": str(tenant_id),
backend/app\llm\budget_policy.py:321:        tenant_id: UUID,
backend/app\llm\budget_policy.py:326:        correlation_id: Optional[str],
backend/app\llm\budget_policy.py:333:                    tenant_id, request_id, correlation_id,
backend/app\llm\budget_policy.py:339:                    :tenant_id, :request_id, :correlation_id,
backend/app\llm\budget_policy.py:347:                "tenant_id": str(tenant_id),
backend/app\llm\budget_policy.py:349:                "correlation_id": correlation_id,
backend/app\models\base.py:30:    - tenant_id column for RLS policy evaluation
backend/app\models\base.py:34:        Sessions must set `app.current_tenant_id` session variable using
backend/app\models\base.py:35:        `get_session(tenant_id)` from app.db.session module.
backend/app\models\base.py:38:    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
backend/app\models\attribution_event.py:37:    RLS Enabled: Yes (tenant_id isolation via app.current_tenant_id)
backend/app\models\attribution_event.py:38:    Idempotency: Enforced via UNIQUE(tenant_id, idempotency_key)
backend/app\models\attribution_event.py:59:    # Timestamps (inherited tenant_id, created_at, updated_at from TenantMixin)
backend/app\models\attribution_event.py:64:    correlation_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
backend/app\models\attribution_event.py:115:            "tenant_id",
backend/app\models\attribution_event.py:117:            name="uq_attribution_events_tenant_idempotency_key",
backend/app\services\revenue_reconciliation.py:57:    tenant_id: UUID
backend/app\services\revenue_reconciliation.py:90:        tenant_id: UUID,
backend/app\services\revenue_reconciliation.py:102:            tenant_id: The tenant UUID.
backend/app\services\revenue_reconciliation.py:145:            tenant_id=tenant_id,
backend/app\services\revenue_reconciliation.py:161:                "tenant_id": str(tenant_id),
backend/app\services\revenue_reconciliation.py:172:            tenant_id=tenant_id,
backend/app\services\revenue_reconciliation.py:188:        tenant_id: UUID,
backend/app\services\revenue_reconciliation.py:209:                    id, tenant_id, order_id, transaction_id, state,
backend/app\services\revenue_reconciliation.py:214:                    :id, :tenant_id, :order_id, :transaction_id, 'captured',
backend/app\services\revenue_reconciliation.py:224:                "tenant_id": str(tenant_id),
backend/app\services\revenue_reconciliation.py:251:                WHERE tenant_id = :tenant_id
backend/app\services\revenue_reconciliation.py:255:            {"tenant_id": str(tenant_id), "transaction_id": transaction_id},
backend/app\services\revenue_reconciliation.py:263:        tenant_id: UUID,
backend/app\services\revenue_reconciliation.py:271:            tenant_id: The tenant UUID.
backend/app\services\revenue_reconciliation.py:286:                WHERE tenant_id = :tenant_id AND order_id = :order_id
backend/app\services\revenue_reconciliation.py:290:            {"tenant_id": str(tenant_id), "order_id": order_id},
backend/app\services\revenue_reconciliation.py:297:            tenant_id=tenant_id,
backend/app\schemas\llm_payloads.py:16:    tenant_id: UUID = Field(..., description="Tenant context for RLS")
backend/app\schemas\llm_payloads.py:17:    correlation_id: Optional[str] = Field(None, description="Correlation for observability")
backend/app\middleware\observability.py:8:    set_request_correlation_id,
backend/app\middleware\observability.py:9:    set_business_correlation_id,
backend/app\middleware\observability.py:10:    set_tenant_id,
backend/app\middleware\observability.py:11:    get_request_correlation_id,
backend/app\middleware\observability.py:17:    Captures correlation_id from header (X-Correlation-ID) or generates one.
backend/app\middleware\observability.py:18:    Adds the correlation_id to response headers and initializes tenant_id context (filled later).
backend/app\middleware\observability.py:22:        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
backend/app\middleware\observability.py:23:        set_request_correlation_id(correlation_id)
backend/app\middleware\observability.py:25:        set_business_correlation_id(None)
backend/app\middleware\observability.py:26:        set_tenant_id(None)
backend/app\middleware\observability.py:29:        response.headers["X-Correlation-ID"] = get_request_correlation_id() or correlation_id
backend/app\db\session.py:5:applies the `app.current_tenant_id` session variable required for PostgreSQL
backend/app\db\session.py:87:async def get_session(tenant_id: UUID) -> AsyncGenerator[AsyncSession, None]:
backend/app\db\session.py:91:    The session variable `app.current_tenant_id` is set before yielding the
backend/app\db\session.py:99:                "SELECT set_config('app.current_tenant_id', :tenant_id, false)"
backend/app\db\session.py:101:            {"tenant_id": str(tenant_id)},
backend/app\db\session.py:127:async def set_tenant_guc_async(
backend/app\db\session.py:128:    session: AsyncConnection | AsyncSession, tenant_id: UUID, local: bool = True
backend/app\db\session.py:131:    Async helper to set tenant context (app.current_tenant_id) on an existing session/connection.
backend/app\db\session.py:135:        tenant_id: UUID tenant context value
backend/app\db\session.py:139:        text("SELECT set_config('app.current_tenant_id', :tenant_id, :is_local)"),
backend/app\db\session.py:140:        {"tenant_id": str(tenant_id), "is_local": local},
backend/app\db\session.py:144:def set_tenant_guc_sync(
backend/app\db\session.py:145:    session: Connection, tenant_id: UUID, local: bool = True
backend/app\db\session.py:148:    Sync helper to set tenant context (app.current_tenant_id) on an existing sync connection.
backend/app\db\session.py:154:        text("SELECT set_config('app.current_tenant_id', :tenant_id, :is_local)"),
backend/app\db\session.py:155:        {"tenant_id": str(tenant_id), "is_local": local},
backend/app\db\session.py:160:async def set_tenant_guc(session: AsyncSession, tenant_id: UUID, local: bool = True) -> None:
backend/app\db\session.py:161:    await set_tenant_guc_async(session, tenant_id, local)
backend/app\models\__init__.py:21:    async with get_session(tenant_id=some_uuid) as session:
backend/app\observability\logging_config.py:4:Uses JSON-formatted logs with correlation_id and tenant_id context.
backend/app\observability\logging_config.py:11:    get_request_correlation_id,
backend/app\observability\logging_config.py:12:    get_business_correlation_id,
backend/app\observability\logging_config.py:13:    get_tenant_id,
backend/app\observability\logging_config.py:29:        cid_req = getattr(record, "correlation_id_request", None) or get_request_correlation_id()
backend/app\observability\logging_config.py:30:        cid_bus = getattr(record, "correlation_id_business", None) or get_business_correlation_id()
backend/app\observability\logging_config.py:31:        tid = getattr(record, "tenant_id", None) or get_tenant_id()
backend/app\observability\logging_config.py:33:            log["correlation_id_request"] = cid_req
backend/app\observability\logging_config.py:35:            log["correlation_id_business"] = cid_bus
backend/app\observability\logging_config.py:37:            log["tenant_id"] = tid
backend/app\ingestion\event_service.py:65:        tenant_id: UUID,
backend/app\ingestion\event_service.py:74:            session: Database session with RLS context set (app.current_tenant_id)
backend/app\ingestion\event_service.py:75:            tenant_id: Tenant UUID for event ownership
backend/app\ingestion\event_service.py:92:        existing = await self._check_duplicate(session, tenant_id, idempotency_key)
backend/app\ingestion\event_service.py:100:                    "tenant_id": str(tenant_id),
backend/app\ingestion\event_service.py:120:                tenant_id=str(tenant_id)
backend/app\ingestion\event_service.py:126:                tenant_id=tenant_id,
backend/app\ingestion\event_service.py:136:                correlation_id=validated.get("correlation_id"),
backend/app\ingestion\event_service.py:159:                    "tenant_id": str(tenant_id),
backend/app\ingestion\event_service.py:161:                    "correlation_id_business": idempotency_key,
backend/app\ingestion\event_service.py:181:                    "tenant_id": str(tenant_id),
backend/app\ingestion\event_service.py:184:                    "correlation_id_business": idempotency_key,
backend/app\ingestion\event_service.py:190:                tenant_id=tenant_id,
backend/app\ingestion\event_service.py:207:                and ("idempotency" in msg or "uq_attribution_events_tenant_idempotency_key" in msg)
backend/app\ingestion\event_service.py:213:            existing_after_race = await self._check_duplicate(session, tenant_id, idempotency_key)
backend/app\ingestion\event_service.py:221:                        "tenant_id": str(tenant_id),
backend/app\ingestion\event_service.py:234:        self, session: AsyncSession, tenant_id: UUID, idempotency_key: str
backend/app\ingestion\event_service.py:251:                AttributionEvent.tenant_id == tenant_id,
backend/app\ingestion\event_service.py:321:        # Optional: correlation_id
backend/app\ingestion\event_service.py:322:        if "correlation_id" in event_data and event_data["correlation_id"]:
backend/app\ingestion\event_service.py:324:                if isinstance(event_data["correlation_id"], UUID):
backend/app\ingestion\event_service.py:325:                    validated["correlation_id"] = event_data["correlation_id"]
backend/app\ingestion\event_service.py:327:                    validated["correlation_id"] = UUID(str(event_data["correlation_id"]))
backend/app\ingestion\event_service.py:329:                # Ignore invalid correlation_id (optional field)
backend/app\ingestion\event_service.py:330:                validated["correlation_id"] = None
backend/app\ingestion\event_service.py:332:            validated["correlation_id"] = None
backend/app\ingestion\event_service.py:339:        tenant_id: UUID,
backend/app\ingestion\event_service.py:354:            tenant_id: Tenant UUID
backend/app\ingestion\event_service.py:374:        correlation_id = (
backend/app\ingestion\event_service.py:375:            event_data.get("correlation_id")
backend/app\ingestion\event_service.py:383:            tenant_id=tenant_id,
backend/app\ingestion\event_service.py:386:            correlation_id=correlation_id,
backend/app\ingestion\event_service.py:397:    tenant_id: UUID,
backend/app\ingestion\event_service.py:409:        tenant_id: Tenant UUID (from auth context or API key)
backend/app\ingestion\event_service.py:427:    async with get_session(tenant_id=tenant_id) as session:
backend/app\ingestion\event_service.py:432:                tenant_id=tenant_id,
backend/app\ingestion\event_service.py:451:                extra={"error": str(e), "tenant_id": str(tenant_id)}
backend/app\ingestion\event_service.py:464:                and ("idempotency" in msg or "uq_attribution_events_tenant_idempotency_key" in msg)
backend/app\ingestion\event_service.py:471:                        AttributionEvent.tenant_id == tenant_id,
backend/app\ingestion\event_service.py:488:                extra={"error": str(e), "tenant_id": str(tenant_id)},
backend/app\ingestion\event_service.py:498:                extra={"error": str(e), "tenant_id": str(tenant_id)},
backend/app\tasks\r4_failure_semantics.py:43:    tenant_id: UUID
backend/app\tasks\r4_failure_semantics.py:44:    correlation_id: UUID
backend/app\tasks\r4_failure_semantics.py:54:    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (str(ctx.tenant_id),))
backend/app\tasks\r4_failure_semantics.py:56:    cur.execute("SELECT set_config('app.correlation_id', %s, true)", (str(ctx.correlation_id),))
backend/app\tasks\r4_failure_semantics.py:57:    cur.execute("SELECT current_setting('app.current_tenant_id', true)")
backend/app\tasks\r4_failure_semantics.py:59:    if guc != str(ctx.tenant_id):
backend/app\tasks\r4_failure_semantics.py:60:        raise RuntimeError(f"tenant GUC mismatch: expected={ctx.tenant_id} got={guc}")
backend/app\tasks\r4_failure_semantics.py:73:        "SELECT COALESCE(MAX(attempt_no), 0) FROM r4_task_attempts WHERE tenant_id=%s AND task_id=%s",
backend/app\tasks\r4_failure_semantics.py:74:        (str(ctx.tenant_id), task_id),
backend/app\tasks\r4_failure_semantics.py:79:        INSERT INTO r4_task_attempts (tenant_id, task_id, scenario, attempt_no, worker_pid)
backend/app\tasks\r4_failure_semantics.py:82:        (str(ctx.tenant_id), task_id, scenario, attempt_no, worker_pid),
backend/app\tasks\r4_failure_semantics.py:98:        INSERT INTO r4_crash_barriers (tenant_id, task_id, scenario, attempt_no, worker_pid)
backend/app\tasks\r4_failure_semantics.py:100:        ON CONFLICT (tenant_id, task_id, attempt_no) DO NOTHING
backend/app\tasks\r4_failure_semantics.py:102:        (str(ctx.tenant_id), task_id, scenario, attempt_no, worker_pid),
backend/app\tasks\r4_failure_semantics.py:113:def poison_pill(self, *, tenant_id: str, correlation_id: str, marker: str) -> None:
backend/app\tasks\r4_failure_semantics.py:117:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:118:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:119:    ctx = DbCtx(tenant_id=tenant_uuid, correlation_id=correlation_uuid)
backend/app\tasks\r4_failure_semantics.py:138:            "tenant_id": str(tenant_uuid),
backend/app\tasks\r4_failure_semantics.py:139:            "correlation_id": str(correlation_uuid),
backend/app\tasks\r4_failure_semantics.py:168:def crash_after_write_pre_ack(self, *, tenant_id: str, correlation_id: str, effect_key: str) -> dict[str, str | int]:
backend/app\tasks\r4_failure_semantics.py:176:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:177:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:178:    ctx = DbCtx(tenant_id=tenant_uuid, correlation_id=correlation_uuid)
backend/app\tasks\r4_failure_semantics.py:196:                INSERT INTO worker_side_effects (tenant_id, task_id, correlation_id, effect_key)
backend/app\tasks\r4_failure_semantics.py:198:                ON CONFLICT (tenant_id, task_id) DO NOTHING
backend/app\tasks\r4_failure_semantics.py:226:            "tenant_id": str(tenant_uuid),
backend/app\tasks\r4_failure_semantics.py:227:            "correlation_id": str(correlation_uuid),
backend/app\tasks\r4_failure_semantics.py:241:                "tenant_id": str(tenant_uuid),
backend/app\tasks\r4_failure_semantics.py:242:                "correlation_id": str(correlation_uuid),
backend/app\tasks\r4_failure_semantics.py:259:    tenant_id: str,
backend/app\tasks\r4_failure_semantics.py:260:    correlation_id: str,
backend/app\tasks\r4_failure_semantics.py:263:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:264:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:266:    ctx = DbCtx(tenant_id=tenant_uuid, correlation_id=correlation_uuid)
backend/app\tasks\r4_failure_semantics.py:287:        "tenant_id": str(tenant_uuid),
backend/app\tasks\r4_failure_semantics.py:301:def runaway_sleep(self, *, tenant_id: str, correlation_id: str, sleep_s: int) -> dict[str, str]:
backend/app\tasks\r4_failure_semantics.py:305:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:306:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:310:            "tenant_id": str(tenant_uuid),
backend/app\tasks\r4_failure_semantics.py:311:            "correlation_id": str(correlation_uuid),
backend/app\tasks\r4_failure_semantics.py:322:            extra={"task_id": self.request.id, "tenant_id": str(tenant_uuid), "correlation_id": str(correlation_uuid)},
backend/app\tasks\r4_failure_semantics.py:329:def sentinel_side_effect(self, *, tenant_id: str, correlation_id: str, effect_key: str) -> dict[str, str]:
backend/app\tasks\r4_failure_semantics.py:330:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:331:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:332:    ctx = DbCtx(tenant_id=tenant_uuid, correlation_id=correlation_uuid)
backend/app\tasks\r4_failure_semantics.py:339:                INSERT INTO worker_side_effects (tenant_id, task_id, correlation_id, effect_key)
backend/app\tasks\r4_failure_semantics.py:341:                ON CONFLICT (tenant_id, task_id) DO NOTHING
backend/app\tasks\r4_failure_semantics.py:351:def privilege_probes(self, *, tenant_id: str, correlation_id: str) -> dict[str, dict[str, str]]:
backend/app\tasks\r4_failure_semantics.py:356:    tenant_uuid = _require_uuid(tenant_id, name="tenant_id")
backend/app\tasks\r4_failure_semantics.py:357:    correlation_uuid = _require_uuid(correlation_id, name="correlation_id")
backend/app\tasks\r4_failure_semantics.py:358:    ctx = DbCtx(tenant_id=tenant_uuid, correlation_id=correlation_uuid)
backend/app\observability\metrics_policy.py:8:- tenant_id (privacy + unbounded cardinality)
backend/app\observability\metrics_policy.py:211:    # - events_* metrics: no labels (aggregate only, tenant_id removed)
backend/app\models\dead_event.py:24:    RLS Enabled: Yes (tenant_id isolation via app.current_tenant_id)
backend/app\models\dead_event.py:54:    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
backend/app\models\dead_event.py:68:    correlation_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
backend/app\services\llm_dispatch.py:27:        "tenant_id": payload.tenant_id,
backend/app\services\llm_dispatch.py:28:        "correlation_id": payload.correlation_id,
backend/app\models\llm.py:38:    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
backend/app\models\llm.py:66:            "tenant_id",
backend/app\models\llm.py:85:    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
backend/app\models\llm.py:99:            "tenant_id",
backend/app\models\llm.py:119:    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
backend/app\models\llm.py:162:    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
backend/app\observability\metrics.py:5:No tenant_id, UUID, or unbounded user-supplied values are permitted.
backend/app\observability\metrics.py:32:# Removed: tenant_id, vendor, event_type, error_type labels
backend/app\observability\metrics.py:33:# Rationale: tenant_id is PII/unbounded; vendor/event_type/error_type are
backend/app\observability\context.py:8:correlation_id_request_var: ContextVar[Optional[str]] = ContextVar("correlation_id_request", default=None)
backend/app\observability\context.py:9:correlation_id_business_var: ContextVar[Optional[str]] = ContextVar("correlation_id_business", default=None)
backend/app\observability\context.py:10:tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
backend/app\observability\context.py:13:def set_request_correlation_id(value: str) -> None:
backend/app\observability\context.py:14:    correlation_id_request_var.set(value)
backend/app\observability\context.py:17:def get_request_correlation_id() -> Optional[str]:
backend/app\observability\context.py:18:    return correlation_id_request_var.get()
backend/app\observability\context.py:21:def set_business_correlation_id(value: Optional[str]) -> None:
backend/app\observability\context.py:22:    correlation_id_business_var.set(value)
backend/app\observability\context.py:25:def get_business_correlation_id() -> Optional[str]:
backend/app\observability\context.py:26:    return correlation_id_business_var.get()
backend/app\observability\context.py:29:def set_tenant_id(value: Optional[UUID]) -> None:
backend/app\observability\context.py:30:    tenant_id_var.set(str(value) if value else None)
backend/app\observability\context.py:33:def get_tenant_id() -> Optional[str]:
backend/app\observability\context.py:34:    return tenant_id_var.get()
backend/app\observability\context.py:40:        "correlation_id_request": get_request_correlation_id(),
backend/app\observability\context.py:41:        "correlation_id_business": get_business_correlation_id(),
backend/app\observability\context.py:42:        "tenant_id": get_tenant_id(),
backend/app\tasks\health.py:17:from app.observability.context import set_request_correlation_id
backend/app\tasks\health.py:52:    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
backend/app\tasks\health.py:53:    set_request_correlation_id(correlation_id)
backend/app\tasks\health.py:57:            extra={"task_name": self.name, "task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\health.py:76:                "correlation_id": correlation_id,
backend/app\tasks\health.py:81:        set_request_correlation_id(None)
backend/app\ingestion\channel_normalization.py:112:    tenant_id: Optional[str] = None
backend/app\ingestion\channel_normalization.py:124:        tenant_id: Tenant experiencing the unmapped channel (if available)
backend/app\ingestion\channel_normalization.py:134:            "tenant_id": tenant_id,
backend/app\ingestion\channel_normalization.py:165:    tenant_id: Optional[str] = None
backend/app\ingestion\channel_normalization.py:185:        tenant_id: Optional tenant ID for logging context
backend/app\ingestion\channel_normalization.py:229:        log_unmapped_channel(raw_key, utm_source, utm_medium, vendor="unknown", tenant_id=tenant_id)
backend/app\ingestion\channel_normalization.py:236:        log_unmapped_channel(raw_key, utm_source, utm_medium, vendor, tenant_id)
backend/app\ingestion\channel_normalization.py:289:                    "tenant_id": tenant_id,
backend/app\ingestion\channel_normalization.py:295:    log_unmapped_channel(raw_key, utm_source, utm_medium, vendor, tenant_id)
backend/app\tasks\maintenance.py:22:from app.db.session import engine, set_tenant_guc
backend/app\tasks\maintenance.py:23:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\maintenance.py:32:    view_name: str, task_id: Optional[str] = None, tenant_id: Optional[UUID] = None
backend/app\tasks\maintenance.py:48:                "tenant_id": str(tenant_id) if tenant_id else None,
backend/app\tasks\maintenance.py:57:    view_name: str, task_id: Optional[str] = None, tenant_id: Optional[UUID] = None
backend/app\tasks\maintenance.py:62:    quoted_view = _validated_matview_identifier(view_name, task_id=task_id, tenant_id=tenant_id)
backend/app\tasks\maintenance.py:85:    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
backend/app\tasks\maintenance.py:86:    set_request_correlation_id(correlation_id)
backend/app\tasks\maintenance.py:90:            result = refresh_single(view_name, None, correlation_id)
backend/app\tasks\maintenance.py:99:            extra={"task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\maintenance.py:103:        set_request_correlation_id(None)
backend/app\tasks\maintenance.py:114:def refresh_matview_for_tenant(self, tenant_id: UUID, view_name: str, correlation_id: Optional[str] = None) -> Dict[str, str]:
backend/app\tasks\maintenance.py:122:        tenant_id: UUID of tenant scope
backend/app\tasks\maintenance.py:124:        correlation_id: Optional correlation ID for tracing
backend/app\tasks\maintenance.py:127:        Dict with status, view_name, tenant_id, and result ("success" or "skipped_already_running")
backend/app\tasks\maintenance.py:132:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\maintenance.py:133:    set_request_correlation_id(correlation_id)
backend/app\tasks\maintenance.py:134:    set_tenant_id(tenant_id)
backend/app\tasks\maintenance.py:137:        _qualified_matview_identifier(view_name, task_id=self.request.id, tenant_id=tenant_id)
backend/app\tasks\maintenance.py:138:        result = refresh_single(view_name, tenant_id, correlation_id)
backend/app\tasks\maintenance.py:143:                "tenant_id": str(tenant_id),
backend/app\tasks\maintenance.py:145:                "correlation_id": correlation_id,
backend/app\tasks\maintenance.py:154:            "tenant_id": str(tenant_id),
backend/app\tasks\maintenance.py:163:                "tenant_id": str(tenant_id),
backend/app\tasks\maintenance.py:165:                "correlation_id": correlation_id,
backend/app\tasks\maintenance.py:171:async def _validate_db_connection_for_tenant(tenant_id: UUID) -> str:
backend/app\tasks\maintenance.py:173:        await set_tenant_guc(conn, tenant_id, local=False)
backend/app\tasks\maintenance.py:174:        res = await conn.execute(text("SELECT current_setting('app.current_tenant_id')"))
backend/app\tasks\maintenance.py:185:def scan_for_pii_contamination_task(self, tenant_id: UUID, correlation_id: Optional[str] = None) -> Dict[str, str]:
backend/app\tasks\maintenance.py:189:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\maintenance.py:190:    set_request_correlation_id(correlation_id)
backend/app\tasks\maintenance.py:191:    set_tenant_id(tenant_id)
backend/app\tasks\maintenance.py:193:        current = asyncio.run(_validate_db_connection_for_tenant(tenant_id))
backend/app\tasks\maintenance.py:196:            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\maintenance.py:198:        return {"status": "ok", "tenant_id": str(tenant_id), "guc": current}
backend/app\tasks\maintenance.py:203:            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\maintenance.py:208:async def _enforce_retention(tenant_id: UUID, cutoff_90: datetime, cutoff_30: datetime) -> Dict[str, int]:
backend/app\tasks\maintenance.py:216:        await set_tenant_guc(conn, tenant_id, local=False)
backend/app\tasks\maintenance.py:248:def enforce_data_retention_task(self, tenant_id: UUID, correlation_id: Optional[str] = None) -> Dict[str, int]:
backend/app\tasks\maintenance.py:252:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\maintenance.py:253:    set_request_correlation_id(correlation_id)
backend/app\tasks\maintenance.py:254:    set_tenant_id(tenant_id)
backend/app\tasks\maintenance.py:258:        results = asyncio.run(_enforce_retention(tenant_id, cutoff_90_day, cutoff_30_day))
backend/app\tasks\maintenance.py:262:                "tenant_id": str(tenant_id),
backend/app\tasks\maintenance.py:264:                "correlation_id": correlation_id,
backend/app\tasks\maintenance.py:273:            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\llm.py:15:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\llm.py:29:    correlation = model.correlation_id or model.request_id or "unknown"
backend/app\tasks\llm.py:30:    set_request_correlation_id(correlation)
backend/app\tasks\llm.py:31:    set_tenant_id(model.tenant_id)
backend/app\tasks\llm.py:39:def _stable_request_id(tenant_id: UUID, endpoint: str, correlation_id: str) -> str:
backend/app\tasks\llm.py:40:    seed = f"{tenant_id}:{endpoint}:{correlation_id}"
backend/app\tasks\llm.py:46:    tenant_id: UUID,
backend/app\tasks\llm.py:48:    correlation_id: Optional[str],
backend/app\tasks\llm.py:52:    correlation = correlation_id or request_id or task_id or "unknown"
backend/app\tasks\llm.py:53:    request = request_id or _stable_request_id(tenant_id, endpoint, correlation)
backend/app\tasks\llm.py:60:    tenant_id: UUID,
backend/app\tasks\llm.py:61:    correlation_id: str,
backend/app\tasks\llm.py:67:        "tenant_id": tenant_id,
backend/app\tasks\llm.py:68:        "correlation_id": correlation_id,
backend/app\tasks\llm.py:85:    tenant_id: UUID,
backend/app\tasks\llm.py:86:    correlation_id: Optional[str] = None,
backend/app\tasks\llm.py:92:        tenant_id=tenant_id,
backend/app\tasks\llm.py:94:        correlation_id=correlation_id,
backend/app\tasks\llm.py:100:            "tenant_id": tenant_id,
backend/app\tasks\llm.py:101:            "correlation_id": correlation,
backend/app\tasks\llm.py:110:        extra={"task_id": self.request.id, "tenant_id": str(model.tenant_id), "correlation_id": correlation, "max_cost_cents": model.max_cost_cents},
backend/app\tasks\llm.py:113:        async with get_session(tenant_id=model.tenant_id) as session:
backend/app\tasks\llm.py:123:                tenant_id=tenant_id,
backend/app\tasks\llm.py:124:                correlation_id=correlation,
backend/app\tasks\llm.py:136:    tenant_id: UUID,
backend/app\tasks\llm.py:137:    correlation_id: Optional[str] = None,
backend/app\tasks\llm.py:143:        tenant_id=tenant_id,
backend/app\tasks\llm.py:145:        correlation_id=correlation_id,
backend/app\tasks\llm.py:151:            "tenant_id": tenant_id,
backend/app\tasks\llm.py:152:            "correlation_id": correlation,
backend/app\tasks\llm.py:161:        extra={"task_id": self.request.id, "tenant_id": str(model.tenant_id), "correlation_id": correlation, "max_cost_cents": model.max_cost_cents},
backend/app\tasks\llm.py:164:        async with get_session(tenant_id=model.tenant_id) as session:
backend/app\tasks\llm.py:178:                tenant_id=tenant_id,
backend/app\tasks\llm.py:179:                correlation_id=correlation,
backend/app\tasks\llm.py:191:    tenant_id: UUID,
backend/app\tasks\llm.py:192:    correlation_id: Optional[str] = None,
backend/app\tasks\llm.py:198:        tenant_id=tenant_id,
backend/app\tasks\llm.py:200:        correlation_id=correlation_id,
backend/app\tasks\llm.py:206:            "tenant_id": tenant_id,
backend/app\tasks\llm.py:207:            "correlation_id": correlation,
backend/app\tasks\llm.py:216:        extra={"task_id": self.request.id, "tenant_id": str(model.tenant_id), "correlation_id": correlation, "max_cost_cents": model.max_cost_cents},
backend/app\tasks\llm.py:219:        async with get_session(tenant_id=model.tenant_id) as session:
backend/app\tasks\llm.py:233:                tenant_id=tenant_id,
backend/app\tasks\llm.py:234:                correlation_id=correlation,
backend/app\tasks\llm.py:246:    tenant_id: UUID,
backend/app\tasks\llm.py:247:    correlation_id: Optional[str] = None,
backend/app\tasks\llm.py:253:        tenant_id=tenant_id,
backend/app\tasks\llm.py:255:        correlation_id=correlation_id,
backend/app\tasks\llm.py:261:            "tenant_id": tenant_id,
backend/app\tasks\llm.py:262:            "correlation_id": correlation,
backend/app\tasks\llm.py:271:        extra={"task_id": self.request.id, "tenant_id": str(model.tenant_id), "correlation_id": correlation, "max_cost_cents": model.max_cost_cents},
backend/app\tasks\llm.py:274:        async with get_session(tenant_id=model.tenant_id) as session:
backend/app\tasks\llm.py:288:                tenant_id=tenant_id,
backend/app\tasks\llm.py:289:                correlation_id=correlation,
backend/app\ingestion\dlq_handler.py:170:        tenant_id: UUID,
backend/app\ingestion\dlq_handler.py:173:        correlation_id: str,
backend/app\ingestion\dlq_handler.py:181:            tenant_id: Tenant UUID
backend/app\ingestion\dlq_handler.py:184:            correlation_id: Idempotency key or unique identifier
backend/app\ingestion\dlq_handler.py:200:        # Convert correlation_id to UUID if it's a string (or None if invalid)
backend/app\ingestion\dlq_handler.py:202:        if correlation_id:
backend/app\ingestion\dlq_handler.py:204:                if isinstance(correlation_id, UUID):
backend/app\ingestion\dlq_handler.py:205:                    correlation_uuid = correlation_id
backend/app\ingestion\dlq_handler.py:207:                    correlation_uuid = UUID(str(correlation_id))
backend/app\ingestion\dlq_handler.py:214:            tenant_id=tenant_id,
backend/app\ingestion\dlq_handler.py:217:            correlation_id=correlation_uuid,
backend/app\ingestion\dlq_handler.py:239:                "tenant_id": str(tenant_id),
backend/app\ingestion\dlq_handler.py:243:                "correlation_id_business": correlation_id,
backend/app\ingestion\dlq_handler.py:329:                tenant_id=dead_event.tenant_id,
backend/app\tasks\matviews.py:19:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\matviews.py:86:def _normalize_tenant_id(value: UUID | str) -> UUID:
backend/app\tasks\matviews.py:116:def _fetch_tenant_ids_sync() -> list[UUID]:
backend/app\tasks\matviews.py:133:    tenant_id: UUID,
backend/app\tasks\matviews.py:134:    correlation_id: str,
backend/app\tasks\matviews.py:143:            "tenant_id": str(tenant_id),
backend/app\tasks\matviews.py:144:            "correlation_id": correlation_id,
backend/app\tasks\matviews.py:161:        "tenant_id": str(result.tenant_id) if result.tenant_id else None,
backend/app\tasks\matviews.py:162:        "correlation_id": result.correlation_id,
backend/app\tasks\matviews.py:184:        "tenant_id": str(result.tenant_id) if result.tenant_id else None,
backend/app\tasks\matviews.py:185:        "correlation_id": result.correlation_id,
backend/app\tasks\matviews.py:227:    tenant_id: UUID,
backend/app\tasks\matviews.py:229:    correlation_id: Optional[str] = None,
backend/app\tasks\matviews.py:233:    tenant_uuid = _normalize_tenant_id(tenant_id)
backend/app\tasks\matviews.py:234:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\matviews.py:235:    set_tenant_id(tenant_uuid)
backend/app\tasks\matviews.py:236:    set_request_correlation_id(correlation_id)
backend/app\tasks\matviews.py:240:        tenant_id=tenant_uuid,
backend/app\tasks\matviews.py:241:        correlation_id=correlation_id,
backend/app\tasks\matviews.py:245:    result = refresh_single(view_name, tenant_uuid, correlation_id)
backend/app\tasks\matviews.py:264:        set_tenant_id(None)
backend/app\tasks\matviews.py:265:        set_request_correlation_id(None)
backend/app\tasks\matviews.py:278:    tenant_id: UUID,
backend/app\tasks\matviews.py:279:    correlation_id: Optional[str] = None,
backend/app\tasks\matviews.py:282:    tenant_uuid = _normalize_tenant_id(tenant_id)
backend/app\tasks\matviews.py:283:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\matviews.py:284:    set_tenant_id(tenant_uuid)
backend/app\tasks\matviews.py:285:    set_request_correlation_id(correlation_id)
backend/app\tasks\matviews.py:290:            "tenant_id": str(tenant_uuid),
backend/app\tasks\matviews.py:291:            "correlation_id": correlation_id,
backend/app\tasks\matviews.py:295:    results = refresh_all_for_tenant(tenant_uuid, correlation_id)
backend/app\tasks\matviews.py:329:            set_tenant_id(None)
backend/app\tasks\matviews.py:330:            set_request_correlation_id(None)
backend/app\tasks\matviews.py:339:        set_tenant_id(None)
backend/app\tasks\matviews.py:340:        set_request_correlation_id(None)
backend/app\tasks\matviews.py:352:    correlation_id: Optional[str] = None,
backend/app\tasks\matviews.py:355:    correlation_id = correlation_id or str(uuid4())
backend/app\tasks\matviews.py:356:    set_request_correlation_id(correlation_id)
backend/app\tasks\matviews.py:362:                "correlation_id": correlation_id,
backend/app\tasks\matviews.py:366:        tenant_ids = _fetch_tenant_ids_sync()
backend/app\tasks\matviews.py:367:        for tenant_id in tenant_ids:
backend/app\tasks\matviews.py:369:                tenant_id=str(tenant_id),
backend/app\tasks\matviews.py:370:                correlation_id=correlation_id,
backend/app\tasks\matviews.py:377:                "correlation_id": correlation_id,
backend/app\tasks\matviews.py:378:                "tenant_count": len(tenant_ids),
backend/app\tasks\matviews.py:382:        return {"status": "ok", "tenant_count": len(tenant_ids), "correlation_id": correlation_id}
backend/app\tasks\matviews.py:384:        set_request_correlation_id(None)
backend/app\models\channel_taxonomy.py:48:        This model does NOT inherit TenantMixin (no tenant_id column).
backend/app\tasks\attribution.py:24:from app.db.session import set_tenant_guc
backend/app\tasks\attribution.py:25:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\attribution.py:49:    tenant_id: UUID = Field(..., description="Tenant context for RLS")
backend/app\tasks\attribution.py:50:    correlation_id: Optional[str] = Field(None, description="Correlation for observability")
backend/app\tasks\attribution.py:57:    correlation = model.correlation_id or str(uuid4())
backend/app\tasks\attribution.py:58:    set_request_correlation_id(correlation)
backend/app\tasks\attribution.py:59:    set_tenant_id(model.tenant_id)
backend/app\tasks\attribution.py:99:    tenant_id: UUID,
backend/app\tasks\attribution.py:106:        f"{tenant_id}:{event_id}:{model_version}:{channel_code}",
backend/app\tasks\attribution.py:121:    tenant_id: UUID,
backend/app\tasks\attribution.py:125:    correlation_id: str,
backend/app\tasks\attribution.py:131:    (tenant_id, window_start, window_end, model_version). Rerunning the same
backend/app\tasks\attribution.py:142:        await set_tenant_guc(conn, tenant_id, local=True)
backend/app\tasks\attribution.py:148:                    id, tenant_id, window_start, window_end, model_version,
backend/app\tasks\attribution.py:149:                    status, run_count, last_correlation_id, created_at, updated_at
backend/app\tasks\attribution.py:151:                    :job_id, :tenant_id, :window_start, :window_end, :model_version,
backend/app\tasks\attribution.py:152:                    'running', 1, :correlation_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
backend/app\tasks\attribution.py:154:                ON CONFLICT (tenant_id, window_start, window_end, model_version)
backend/app\tasks\attribution.py:158:                    last_correlation_id = EXCLUDED.last_correlation_id,
backend/app\tasks\attribution.py:165:                "tenant_id": tenant_id,
backend/app\tasks\attribution.py:169:                "correlation_id": uuid4() if correlation_id is None else UUID(correlation_id),
backend/app\tasks\attribution.py:185:                "tenant_id": str(tenant_id),
backend/app\tasks\attribution.py:191:                "correlation_id": correlation_id,
backend/app\tasks\attribution.py:200:    tenant_id: UUID,
backend/app\tasks\attribution.py:211:        tenant_id: Tenant UUID (for RLS enforcement)
backend/app\tasks\attribution.py:217:        await set_tenant_guc(conn, tenant_id, local=True)
backend/app\tasks\attribution.py:225:                  AND tenant_id = :tenant_id
backend/app\tasks\attribution.py:229:                "tenant_id": tenant_id,
backend/app\tasks\attribution.py:238:            "tenant_id": str(tenant_id),
backend/app\tasks\attribution.py:246:    tenant_id: UUID,
backend/app\tasks\attribution.py:289:        await set_tenant_guc(conn, tenant_id, local=True)
backend/app\tasks\attribution.py:302:                            CAST(:tenant_ids AS uuid[]),
backend/app\tasks\attribution.py:315:                            tenant_id,
backend/app\tasks\attribution.py:330:                        tenant_id,
backend/app\tasks\attribution.py:344:                        tenant_id,
backend/app\tasks\attribution.py:381:                WHERE tenant_id = :tenant_id
backend/app\tasks\attribution.py:388:                "tenant_id": tenant_id,
backend/app\tasks\attribution.py:398:                    "tenant_id": str(tenant_id),
backend/app\tasks\attribution.py:415:                "tenant_ids": [],
backend/app\tasks\attribution.py:435:                            tenant_id=tenant_id,
backend/app\tasks\attribution.py:441:                    batch_rows["tenant_ids"].append(tenant_id)
backend/app\tasks\attribution.py:463:                            "tenant_id": str(tenant_id),
backend/app\tasks\attribution.py:475:                "tenant_id": str(tenant_id),
backend/app\tasks\attribution.py:500:    tenant_id: UUID,
backend/app\tasks\attribution.py:503:    correlation_id: Optional[str] = None,
backend/app\tasks\attribution.py:511:    attribution_recompute_jobs table. Rerunning the same (tenant_id, window_start,
backend/app\tasks\attribution.py:518:        tenant_id: Tenant context for RLS enforcement
backend/app\tasks\attribution.py:521:        correlation_id: Request correlation for observability
backend/app\tasks\attribution.py:534:        tenant_id=tenant_id,
backend/app\tasks\attribution.py:535:        correlation_id=correlation_id,
backend/app\tasks\attribution.py:547:                "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:548:                "correlation_id": correlation,
backend/app\tasks\attribution.py:566:                "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:580:            tenant_id=model.tenant_id,
backend/app\tasks\attribution.py:584:            correlation_id=correlation,
backend/app\tasks\attribution.py:592:                "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:605:            "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:606:            "correlation_id": correlation,
backend/app\tasks\attribution.py:619:            tenant_id=model.tenant_id,
backend/app\tasks\attribution.py:629:            tenant_id=model.tenant_id,
backend/app\tasks\attribution.py:638:                "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:639:                "correlation_id": correlation,
backend/app\tasks\attribution.py:659:            "correlation_id": correlation,
backend/app\tasks\attribution.py:667:            tenant_id=model.tenant_id,
backend/app\tasks\attribution.py:678:                "tenant_id": str(model.tenant_id),
backend/app\tasks\attribution.py:679:                "correlation_id": correlation,
backend/app\tasks\housekeeping.py:20:from app.db.session import engine, set_tenant_guc
backend/app\tasks\housekeeping.py:22:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\housekeeping.py:43:async def _fetch_db_user(tenant_id: Optional[UUID] = None) -> str:
backend/app\tasks\housekeeping.py:48:        if tenant_id:
backend/app\tasks\housekeeping.py:49:            await set_tenant_guc(conn, tenant_id, local=False)
backend/app\tasks\housekeeping.py:54:def _fetch_db_user_sync(tenant_id: Optional[UUID] = None) -> str:
backend/app\tasks\housekeeping.py:91:        if tenant_id:
backend/app\tasks\housekeeping.py:92:            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
backend/app\tasks\housekeeping.py:100:def ping(self, fail: bool = False, tenant_id: Optional[str] = None) -> dict:
backend/app\tasks\housekeeping.py:106:        tenant_id: optional UUID string to set tenant GUC (future RLS-aware tasks).
backend/app\tasks\housekeeping.py:108:    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
backend/app\tasks\housekeeping.py:109:    set_request_correlation_id(correlation_id)
backend/app\tasks\housekeeping.py:113:            extra={"task_name": self.name, "task_id": self.request.id, "correlation_id": correlation_id},
backend/app\tasks\housekeeping.py:119:        if tenant_id:
backend/app\tasks\housekeeping.py:121:                tenant_uuid = UUID(str(tenant_id))
backend/app\tasks\housekeeping.py:128:                set_tenant_id(tenant_uuid)
backend/app\tasks\housekeeping.py:145:                "tenant_id": str(tenant_uuid) if tenant_uuid else None,
backend/app\tasks\housekeeping.py:146:                "correlation_id": correlation_id,
backend/app\tasks\housekeeping.py:151:        set_request_correlation_id(None)
backend/app\tasks\housekeeping.py:152:        set_tenant_id(None)
backend/app\tasks\context.py:4:Provides a decorator that enforces tenant_id presence, sets contextvars for
backend/app\tasks\context.py:18:from app.db.session import engine, set_tenant_guc
backend/app\tasks\context.py:19:from app.observability.context import set_request_correlation_id, set_tenant_id
backend/app\tasks\context.py:74:def _normalize_tenant_id(value: Any) -> UUID:
backend/app\tasks\context.py:80:async def _set_tenant_guc_global(tenant_id: UUID) -> None:
backend/app\tasks\context.py:87:            "tenant_id": str(tenant_id),
backend/app\tasks\context.py:92:        # This prevents connection pool reuse from leaking a previous tenant_id into
backend/app\tasks\context.py:94:        await set_tenant_guc(conn, tenant_id, local=True)
backend/app\tasks\context.py:101:        await conn.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
backend/app\tasks\context.py:108:    Enforces tenant_id, sets contextvars for logging, applies tenant GUC, and
backend/app\tasks\context.py:109:    guarantees a correlation_id is present for downstream logs/metrics.
backend/app\tasks\context.py:114:        tenant_id_value = kwargs.get("tenant_id")
backend/app\tasks\context.py:115:        if tenant_id_value is None:
backend/app\tasks\context.py:116:            raise ValueError("tenant_id is required for tenant-scoped tasks")
backend/app\tasks\context.py:118:        tenant_uuid = _normalize_tenant_id(tenant_id_value)
backend/app\tasks\context.py:119:        correlation_id = kwargs.get("correlation_id") or getattr(self.request, "id", None) or "unknown"
backend/app\tasks\context.py:121:        set_tenant_id(tenant_uuid)
backend/app\tasks\context.py:122:        set_request_correlation_id(correlation_id)
backend/app\tasks\context.py:123:        kwargs["tenant_id"] = tenant_uuid
backend/app\tasks\context.py:124:        kwargs["correlation_id"] = correlation_id
backend/app\tasks\context.py:132:                run_in_worker_loop(_set_tenant_guc_global(tenant_uuid))
backend/app\tasks\context.py:138:                        extra={"tenant_id": str(tenant_uuid), "task_name": getattr(self, "name", None)},
backend/app\tasks\context.py:146:                    extra={"tenant_id": str(tenant_uuid), "task_name": getattr(self, "name", None)},
backend/app\tasks\context.py:154:            set_tenant_id(None)
backend/app\tasks\context.py:155:            set_request_correlation_id(None)
```

### 2.5 Find potential payload/secret leak vectors

Command:
```powershell
rg -n "kwargs|args|payload|request\.body|Authorization|token|secret" backend/app
```

Output:
```text
﻿backend/app\workers\llm.py:26:from app.schemas.llm_payloads import LLMTaskPayload
backend/app\workers\llm.py:34:    payload = {
backend/app\workers\llm.py:40:    seed = json.dumps(payload, sort_keys=True, default=str)
backend/app\workers\llm.py:84:            input_tokens=0,
backend/app\workers\llm.py:85:            output_tokens=0,
backend/app\schemas\llm_payloads.py:2:Canonical payload contract for LLM tasks.
backend/app\schemas\llm_payloads.py:24:        description="Opaque prompt/payload structure",
backend/app\llm\budget_policy.py:47:    """Pricing for an LLM model per 1000 tokens."""
backend/app\llm\budget_policy.py:53:# Values in USD per 1000 tokens
backend/app\llm\budget_policy.py:146:        input_tokens: int,
backend/app\llm\budget_policy.py:147:        output_tokens: int,
backend/app\llm\budget_policy.py:154:            input_tokens: Number of input tokens.
backend/app\llm\budget_policy.py:155:            output_tokens: Number of output tokens.
backend/app\llm\budget_policy.py:168:        input_cost = (Decimal(input_tokens) / Decimal(1000)) * pricing.input_per_1k_usd
backend/app\llm\budget_policy.py:169:        output_cost = (Decimal(output_tokens) / Decimal(1000)) * pricing.output_per_1k_usd
backend/app\llm\budget_policy.py:182:        input_tokens: int,
backend/app\llm\budget_policy.py:183:        output_tokens: int,
backend/app\llm\budget_policy.py:193:            input_tokens: Estimated input tokens.
backend/app\llm\budget_policy.py:194:            output_tokens: Estimated output tokens.
backend/app\llm\budget_policy.py:201:        estimated_cents = self.estimate_cost_cents(input_tokens, output_tokens, requested_model)
backend/app\llm\budget_policy.py:242:        fallback_cost = self.estimate_cost_cents(input_tokens, output_tokens, fallback_model)
backend/app\llm\budget_policy.py:266:        input_tokens: int,
backend/app\llm\budget_policy.py:267:        output_tokens: int,
backend/app\llm\budget_policy.py:279:            input_tokens: Estimated input tokens.
backend/app\llm\budget_policy.py:280:            output_tokens: Estimated output tokens.
backend/app\llm\budget_policy.py:288:            input_tokens=input_tokens,
backend/app\llm\budget_policy.py:289:            output_tokens=output_tokens,
backend/app\llm\budget_policy.py:298:            input_tokens=input_tokens,
backend/app\llm\budget_policy.py:299:            output_tokens=output_tokens,
backend/app\llm\budget_policy.py:324:        input_tokens: int,
backend/app\llm\budget_policy.py:325:        output_tokens: int,
backend/app\llm\budget_policy.py:337:                    input_tokens, output_tokens
backend/app\llm\budget_policy.py:343:                    :input_tokens, :output_tokens
backend/app\llm\budget_policy.py:356:                "input_tokens": input_tokens,
backend/app\llm\budget_policy.py:357:                "output_tokens": output_tokens,
backend/app\webhooks\signatures.py:11:def verify_shopify_signature(raw_body: bytes, secret: Optional[str], header: Optional[str]) -> bool:
backend/app\webhooks\signatures.py:12:    if not secret or not header:
backend/app\webhooks\signatures.py:14:    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
backend/app\webhooks\signatures.py:22:def verify_woocommerce_signature(raw_body: bytes, secret: Optional[str], header: Optional[str]) -> bool:
backend/app\webhooks\signatures.py:23:    if not secret or not header:
backend/app\webhooks\signatures.py:25:    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
backend/app\webhooks\signatures.py:34:def verify_stripe_signature(raw_body: bytes, secret: Optional[str], header: Optional[str], tolerance: int = 300) -> bool:
backend/app\webhooks\signatures.py:40:    if not secret or not header:
backend/app\webhooks\signatures.py:53:    signed_payload = f"{timestamp}.{raw_body.decode()}".encode()
backend/app\webhooks\signatures.py:54:    computed = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
backend/app\webhooks\signatures.py:58:def verify_paypal_signature(raw_body: bytes, secret: Optional[str], header: Optional[str]) -> bool:
backend/app\webhooks\signatures.py:62:    if not secret or not header:
backend/app\webhooks\signatures.py:64:    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
backend/app\celery_app.py:236:def _on_worker_parent_init(**kwargs):
backend/app\celery_app.py:258:def _configure_worker_logging(**kwargs):
backend/app\celery_app.py:274:def _on_worker_process_shutdown(pid=None, **kwargs):
backend/app\celery_app.py:305:        sql += "\n          AND payload LIKE :task_name_filter"
backend/app\celery_app.py:318:                    (public.kombu_message.payload::jsonb -> 'headers' ->> 'id'),
backend/app\celery_app.py:319:                    (public.kombu_message.payload::jsonb -> 'headers' ->> 'task_id'),
backend/app\celery_app.py:320:                    (public.kombu_message.payload::jsonb ->> 'id')
backend/app\celery_app.py:505:def _on_worker_ready(sender=None, **kwargs):
backend/app\celery_app.py:514:def _on_task_prerun(task_id, task, **kwargs):
backend/app\celery_app.py:524:def _on_task_postrun(task_id, task, retval, state, **kwargs):
backend/app\celery_app.py:540:def _on_task_failure(task_id=None, exception=None, args=None, kwargs=None, einfo=None, **extra):
backend/app\celery_app.py:659:        if kwargs and 'tenant_id' in kwargs:
backend/app\celery_app.py:661:                tenant_id = UUID(str(kwargs['tenant_id']))
backend/app\celery_app.py:694:        if correlation_id is None and kwargs and "correlation_id" in kwargs:
backend/app\celery_app.py:696:                correlation_id = UUID(str(kwargs["correlation_id"]))
backend/app\celery_app.py:724:            serialized_args = _serialize_for_json(args if args else [])
backend/app\celery_app.py:725:            serialized_kwargs = _serialize_for_json(kwargs if kwargs else {})
backend/app\celery_app.py:750:                    task_args, task_kwargs, tenant_id,
backend/app\celery_app.py:765:                psycopg2.extras.Json(serialized_args),  # G4-JSON: Explicit JSONB encoding with UUID serialization
backend/app\celery_app.py:766:                psycopg2.extras.Json(serialized_kwargs),  # G4-JSON: Explicit JSONB encoding with UUID serialization
backend/app\celery_control.py:19:    def _request(self, command, **kwargs):
backend/app\celery_control.py:25:                kwargs={},
backend/app\celery_control.py:27:            payload = result.get(timeout=timeout)
backend/app\celery_control.py:31:            node = destination or payload.get("worker") or "unknown"
backend/app\celery_control.py:36:        return super()._request(command, **kwargs)
backend/app\core\config.py:128:        description="If set, kombu visibility recovery only requeues messages whose payload contains this substring (e.g., a task name).",
backend/app\db\session.py:32:# Normalize DSN to ensure asyncpg driver is used and map unsupported parameters to connect_args.
backend/app\db\session.py:33:def _build_async_database_url_and_args() -> tuple[str, dict]:
backend/app\db\session.py:47:    connect_args: dict = {}
backend/app\db\session.py:50:        connect_args["ssl"] = ssl.create_default_context()
backend/app\db\session.py:52:        connect_args.setdefault("server_settings", {})["channel_binding"] = channel_binding
backend/app\db\session.py:54:    return sanitized, connect_args
backend/app\db\session.py:57:_ASYNC_DATABASE_URL, _CONNECT_ARGS = _build_async_database_url_and_args()
backend/app\db\session.py:60:engine_kwargs = {
backend/app\db\session.py:61:    "connect_args": _CONNECT_ARGS,
backend/app\db\session.py:67:    engine_kwargs["poolclass"] = NullPool
backend/app\db\session.py:69:    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
backend/app\db\session.py:70:    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
backend/app\db\session.py:75:    **engine_kwargs,
backend/app\middleware\pii_stripping.py:22:- Recursively traverses incoming JSON payloads
backend/app\middleware\pii_stripping.py:53:    # Common vendor payload keys (defense-in-depth)
backend/app\middleware\pii_stripping.py:113:    FastAPI middleware that strips PII from incoming request payloads.
backend/app\middleware\pii_stripping.py:124:        Process request and strip PII from JSON payloads.
backend/app\middleware\pii_stripping.py:144:                    body = await request.body()
backend/app\middleware\pii_stripping.py:150:                            payload = json.loads(body)
backend/app\middleware\pii_stripping.py:157:                        redacted_payload, redacted_keys = strip_pii_keys_recursive(payload)
backend/app\middleware\pii_stripping.py:174:                        redacted_body = json.dumps(redacted_payload).encode('utf-8')
backend/app\middleware\pii_stripping.py:181:                        # Starlette caches request.body() on first read; override cache too.
backend/app\services\llm_dispatch.py:8:from app.schemas.llm_payloads import LLMTaskPayload
backend/app\services\llm_dispatch.py:24:def _payload_to_kwargs(payload: LLMTaskPayload) -> Dict[str, object]:
backend/app\services\llm_dispatch.py:26:        "payload": payload.prompt,
backend/app\services\llm_dispatch.py:27:        "tenant_id": payload.tenant_id,
backend/app\services\llm_dispatch.py:28:        "correlation_id": payload.correlation_id,
backend/app\services\llm_dispatch.py:29:        "request_id": payload.request_id,
backend/app\services\llm_dispatch.py:30:        "max_cost_cents": payload.max_cost_cents,
backend/app\services\llm_dispatch.py:34:def enqueue_llm_task(task_name: str, payload: LLMTaskPayload):
backend/app\services\llm_dispatch.py:36:    Enqueue a deterministic LLM task using the canonical payload contract.
backend/app\services\llm_dispatch.py:41:    return task.apply_async(kwargs=_payload_to_kwargs(payload))
backend/app\core\pg_locks.py:25:    tenant_token: str
backend/app\core\pg_locks.py:32:            "tenant_token": self.tenant_token,
backend/app\core\pg_locks.py:53:    tenant_token = str(tenant_id) if tenant_id else "GLOBAL"
backend/app\core\pg_locks.py:55:    tenant_key = _int32_from_hash(f"tenant:{tenant_token}")
backend/app\core\pg_locks.py:60:        tenant_token=tenant_token,
backend/app\api\health.py:85:            kwargs={},
backend/app\api\auth.py:7:- POST /api/auth/login: Authenticate user and obtain JWT tokens
backend/app\api\auth.py:8:- POST /api/auth/refresh: Refresh access token using refresh token
backend/app\api\auth.py:9:- POST /api/auth/logout: Invalidate tokens and end session
backend/app\api\auth.py:36:    summary="Authenticate user and obtain JWT tokens",
backend/app\api\auth.py:37:    description="Authenticate with email and password to receive access and refresh tokens"
backend/app\api\auth.py:62:        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sample_access_token",
backend/app\api\auth.py:63:        refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sample_refresh_token",
backend/app\api\auth.py:66:        token_type="Bearer"
backend/app\api\auth.py:75:    summary="Refresh access token",
backend/app\api\auth.py:76:    description="Exchange refresh token for new access and refresh tokens"
backend/app\api\auth.py:78:async def refresh_token(
backend/app\api\auth.py:83:    Refresh access token using refresh token.
backend/app\api\auth.py:86:    Production implementation would validate refresh token and generate new tokens.
backend/app\api\auth.py:92:    # Production: validate refresh token, generate new JWT pair
backend/app\api\auth.py:95:        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_token",
backend/app\api\auth.py:96:        refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_refresh_token",
backend/app\api\auth.py:98:        token_type="Bearer"
backend/app\api\auth.py:107:    summary="Logout user and invalidate tokens",
backend/app\api\auth.py:108:    description="Invalidate access and refresh tokens, ending the user session"
backend/app\api\auth.py:114:    Logout user and invalidate tokens.
backend/app\api\auth.py:117:    Production implementation would blacklist tokens or mark session as ended.
backend/app\api\auth.py:123:    # Production: blacklist tokens, mark session ended in database
backend/app\services\attribution.py:35:    """Serialize a UTC datetime to ISO string with Z suffix for task payloads."""
backend/app\services\attribution.py:51:    correlation_id, and propagates that correlation into both task kwargs and
backend/app\services\attribution.py:61:    start_payload = _isoformat_utc(start_dt)
backend/app\services\attribution.py:62:    end_payload = _isoformat_utc(end_dt)
backend/app\services\attribution.py:65:        kwargs={
backend/app\services\attribution.py:67:            "window_start": start_payload,
backend/app\services\attribution.py:68:            "window_end": end_payload,
backend/app\core\tenant_context.py:34:async def get_tenant_with_webhook_secrets(api_key: str) -> dict:
backend/app\core\tenant_context.py:36:    Resolve tenant identity and webhook secrets by tenant API key.
backend/app\core\tenant_context.py:42:        dict with keys: tenant_id (UUID), shopify_webhook_secret, stripe_webhook_secret,
backend/app\core\tenant_context.py:43:        paypal_webhook_secret, woocommerce_webhook_secret
backend/app\core\tenant_context.py:58:                  shopify_webhook_secret,
backend/app\core\tenant_context.py:59:                  stripe_webhook_secret,
backend/app\core\tenant_context.py:60:                  paypal_webhook_secret,
backend/app\core\tenant_context.py:61:                  woocommerce_webhook_secret
backend/app\core\tenant_context.py:76:        "shopify_webhook_secret": row.get("shopify_webhook_secret"),
backend/app\core\tenant_context.py:77:        "stripe_webhook_secret": row.get("stripe_webhook_secret"),
backend/app\core\tenant_context.py:78:        "paypal_webhook_secret": row.get("paypal_webhook_secret"),
backend/app\core\tenant_context.py:79:        "woocommerce_webhook_secret": row.get("woocommerce_webhook_secret"),
backend/app\api\webhooks.py:6:- Verify vendor signatures using per-tenant secrets
backend/app\api\webhooks.py:21:from app.core.tenant_context import get_tenant_with_webhook_secrets
backend/app\api\webhooks.py:59:async def tenant_secrets(request: Request):
backend/app\api\webhooks.py:66:    tenant_info = await get_tenant_with_webhook_secrets(api_key)
backend/app\api\webhooks.py:88:    payload: dict,
backend/app\api\webhooks.py:103:            original_payload=payload,
backend/app\api\webhooks.py:156:    payload: ShopifyOrderCreateRequest = Body(...),
backend/app\api\webhooks.py:158:    tenant_info=Depends(tenant_secrets),
backend/app\api\webhooks.py:160:    raw_body = getattr(request.state, "original_body", None) or await request.body()
backend/app\api\webhooks.py:161:    if not verify_shopify_signature(raw_body, tenant_info["shopify_webhook_secret"], x_shopify_hmac_sha256):
backend/app\api\webhooks.py:167:    if not payload.id:
backend/app\api\webhooks.py:170:    idempotency_key = str(uuid5(NAMESPACE_URL, f"shopify_order_create_{payload.id}"))
backend/app\api\webhooks.py:174:        "event_timestamp": (payload.created_at or datetime.now(timezone.utc)).isoformat(),
backend/app\api\webhooks.py:175:        "revenue_amount": payload.total_price or "0",
backend/app\api\webhooks.py:176:        "currency": payload.currency or "USD",
backend/app\api\webhooks.py:177:        "session_id": str(uuid5(NAMESPACE_URL, f"shopify:{payload.id}")),
backend/app\api\webhooks.py:180:        "external_event_id": str(payload.id),
backend/app\api\webhooks.py:193:    payload: StripePaymentIntentSucceededRequest = Body(...),
backend/app\api\webhooks.py:196:    tenant_info=Depends(tenant_secrets),
backend/app\api\webhooks.py:198:    raw_body = getattr(request.state, "original_body", None) or await request.body()
backend/app\api\webhooks.py:199:    if not verify_stripe_signature(raw_body, tenant_info["stripe_webhook_secret"], stripe_signature):
backend/app\api\webhooks.py:205:    if not payload.id and not x_idempotency_key:
backend/app\api\webhooks.py:208:    idempotency_key = x_idempotency_key or str(uuid5(NAMESPACE_URL, f"stripe_payment_intent_succeeded_{payload.id}"))
backend/app\api\webhooks.py:210:    ts = datetime.fromtimestamp(payload.created) if payload.created else datetime.now(timezone.utc)
backend/app\api\webhooks.py:213:    if payload.amount is not None:
backend/app\api\webhooks.py:214:        revenue_amount = str((Decimal(payload.amount) / Decimal(100)).quantize(Decimal("0.01")))
backend/app\api\webhooks.py:219:        "currency": payload.currency.upper() if payload.currency else "USD",
backend/app\api\webhooks.py:220:        "session_id": str(uuid5(NAMESPACE_URL, f"stripe:{payload.id or idempotency_key}")),
backend/app\api\webhooks.py:223:        "external_event_id": payload.id,
backend/app\api\webhooks.py:236:    payload: dict = Body(...),
backend/app\api\webhooks.py:239:    tenant_info=Depends(tenant_secrets),
backend/app\api\webhooks.py:246:    - PII present (keys stripped by middleware): DLQ with sanitized payload, no canonical insert
backend/app\api\webhooks.py:247:    - Malformed payload: DLQ with sanitized payload, no canonical insert
backend/app\api\webhooks.py:250:    raw_body = getattr(request.state, "original_body", None) or await request.body()
backend/app\api\webhooks.py:251:    if not verify_stripe_signature(raw_body, tenant_info["stripe_webhook_secret"], stripe_signature):
backend/app\api\webhooks.py:264:        event_id = payload.get("id")
backend/app\api\webhooks.py:265:        created_epoch = payload.get("created")
backend/app\api\webhooks.py:266:        obj = (payload.get("data") or {}).get("object") or {}
backend/app\api\webhooks.py:291:            payload={
backend/app\api\webhooks.py:296:                "vendor_payload": payload,
backend/app\api\webhooks.py:323:            payload={
backend/app\api\webhooks.py:328:                "vendor_payload": payload,
backend/app\api\webhooks.py:351:        "vendor_payload": payload,
backend/app\api\webhooks.py:391:    payload: PayPalSaleCompletedRequest = Body(...),
backend/app\api\webhooks.py:393:    tenant_info=Depends(tenant_secrets),
backend/app\api\webhooks.py:395:    raw_body = getattr(request.state, "original_body", None) or await request.body()
backend/app\api\webhooks.py:396:    if not verify_paypal_signature(raw_body, tenant_info["paypal_webhook_secret"], transmission_sig):
backend/app\api\webhooks.py:402:    if not payload.id or not payload.amount:
backend/app\api\webhooks.py:405:    idempotency_key = str(uuid5(NAMESPACE_URL, f"paypal_sale_completed_{payload.id}"))
backend/app\api\webhooks.py:407:    ts = payload.create_time or datetime.now(timezone.utc)
backend/app\api\webhooks.py:411:        "revenue_amount": payload.amount.total or "0",
backend/app\api\webhooks.py:412:        "currency": payload.amount.currency or "USD",
backend/app\api\webhooks.py:413:        "session_id": str(uuid5(NAMESPACE_URL, f"paypal:{payload.id}")),
backend/app\api\webhooks.py:416:        "external_event_id": payload.id,
backend/app\api\webhooks.py:429:    payload: WooCommerceOrderCompletedRequest = Body(...),
backend/app\api\webhooks.py:431:    tenant_info=Depends(tenant_secrets),
backend/app\api\webhooks.py:433:    raw_body = getattr(request.state, "original_body", None) or await request.body()
backend/app\api\webhooks.py:434:    if not verify_woocommerce_signature(raw_body, tenant_info["woocommerce_webhook_secret"], x_wc_webhook_signature):
backend/app\api\webhooks.py:440:    if not payload.id:
backend/app\api\webhooks.py:443:    idempotency_key = str(uuid5(NAMESPACE_URL, f"woocommerce_order_completed_{payload.id}"))
backend/app\api\webhooks.py:445:    ts = payload.date_completed or datetime.now(timezone.utc)
backend/app\api\webhooks.py:449:        "revenue_amount": payload.total or "0",
backend/app\api\webhooks.py:450:        "currency": payload.currency or "USD",
backend/app\api\webhooks.py:451:        "session_id": str(uuid5(NAMESPACE_URL, f"woocommerce:{payload.id}")),
backend/app\api\webhooks.py:454:        "external_event_id": str(payload.id),
backend/app\observability\worker_metrics_exporter.py:45:    def log_message(self, format, *args):  # noqa: A002 - signature required by base class
backend/app\tasks\matviews.py:158:    payload = {
backend/app\tasks\matviews.py:168:        logger.error("matview_refresh_view_failed", extra=payload)
backend/app\tasks\matviews.py:170:        logger.info("matview_refresh_view_completed", extra=payload)
backend/app\tasks\matviews.py:181:    payload = {
backend/app\tasks\matviews.py:192:        logger.error("matview_refresh_task_failed", extra=payload)
backend/app\tasks\matviews.py:194:        logger.info("matview_refresh_task_completed", extra=payload)
backend/app\tasks\attribution.py:37:def _run_async(coro_factory, *args, **kwargs):
backend/app\tasks\attribution.py:44:    coro = coro_factory(*args, **kwargs)
backend/app\ingestion\dlq_handler.py:102:        - PII detection: PII key found in payload (permanent - security violation)
backend/app\ingestion\dlq_handler.py:171:        original_payload: dict,
backend/app\ingestion\dlq_handler.py:182:            original_payload: Original event data that failed ingestion
backend/app\ingestion\dlq_handler.py:216:            raw_payload=original_payload,
backend/app\ingestion\dlq_handler.py:223:            event_type=original_payload.get("event_type", "unknown"),
backend/app\ingestion\dlq_handler.py:246:                "event_type": (original_payload or {}).get("event_type", "unknown"),
backend/app\ingestion\dlq_handler.py:330:                event_data=dead_event.raw_payload,
backend/app\ingestion\event_service.py:76:            event_data: Raw event payload (PII-stripped by middleware)
backend/app\ingestion\event_service.py:135:                raw_payload=event_data,
backend/app\ingestion\event_service.py:268:            event_data: Raw event payload
backend/app\ingestion\event_service.py:355:            event_data: Raw event payload (failed validation)
backend/app\ingestion\event_service.py:384:            original_payload=event_data,
backend/app\ingestion\event_service.py:410:        event_data: Raw event payload (PII-stripped)
backend/app\models\llm.py:48:    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
backend/app\models\llm.py:49:    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
backend/app\models\llm.py:60:    __table_args__ = (
backend/app\models\llm.py:61:        CheckConstraint("input_tokens >= 0", name="ck_llm_api_calls_input_tokens_positive"),
backend/app\models\llm.py:62:        CheckConstraint("output_tokens >= 0", name="ck_llm_api_calls_output_tokens_positive"),
backend/app\models\llm.py:97:    __table_args__ = (
backend/app\models\llm.py:142:    __table_args__ = (
backend/app\models\llm.py:184:    __table_args__ = (
backend/app\models\channel_taxonomy.py:79:    __table_args__ = (
backend/app\models\attribution_event.py:46:        - raw_payload: Original webhook payload (PII-stripped)
backend/app\models\attribution_event.py:71:    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
backend/app\models\attribution_event.py:113:    __table_args__ = (
backend/app\tasks\health.py:64:        payload = {
backend/app\tasks\health.py:79:        return payload
backend/app\models\dead_event.py:27:        Store webhook payloads that fail ingestion validation or processing.
backend/app\models\dead_event.py:32:        - raw_payload: Original webhook payload (PII-stripped)
backend/app\models\dead_event.py:65:    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
backend/app\models\dead_event.py:89:    __table_args__ = (
backend/app\tasks\llm.py:16:from app.schemas.llm_payloads import LLMTaskPayload
backend/app\tasks\llm.py:35:def _run_async(coro_factory, *args, **kwargs):
backend/app\tasks\llm.py:36:    return run_in_worker_loop(coro_factory(*args, **kwargs))
backend/app\tasks\llm.py:57:def _retry_kwargs(
backend/app\tasks\llm.py:59:    payload: dict,
backend/app\tasks\llm.py:66:        "payload": payload,
backend/app\tasks\llm.py:84:    payload: dict,
backend/app\tasks\llm.py:103:            "prompt": payload,
backend/app\tasks\llm.py:121:            kwargs=_retry_kwargs(
backend/app\tasks\llm.py:122:                payload=payload,
backend/app\tasks\llm.py:135:    payload: dict,
backend/app\tasks\llm.py:154:            "prompt": payload,
backend/app\tasks\llm.py:176:            kwargs=_retry_kwargs(
backend/app\tasks\llm.py:177:                payload=payload,
backend/app\tasks\llm.py:190:    payload: dict,
backend/app\tasks\llm.py:209:            "prompt": payload,
backend/app\tasks\llm.py:231:            kwargs=_retry_kwargs(
backend/app\tasks\llm.py:232:                payload=payload,
backend/app\tasks\llm.py:245:    payload: dict,
backend/app\tasks\llm.py:264:            "prompt": payload,
backend/app\tasks\llm.py:286:            kwargs=_retry_kwargs(
backend/app\tasks\llm.py:287:                payload=payload,
backend/app\tasks\housekeeping.py:133:        payload = {
backend/app\tasks\housekeeping.py:149:        return payload
backend/app\tasks\context.py:47:                args=(_WORKER_LOOP,),
backend/app\tasks\context.py:113:    def _wrapped(self, *args, **kwargs):
backend/app\tasks\context.py:114:        tenant_id_value = kwargs.get("tenant_id")
backend/app\tasks\context.py:119:        correlation_id = kwargs.get("correlation_id") or getattr(self.request, "id", None) or "unknown"
backend/app\tasks\context.py:123:        kwargs["tenant_id"] = tenant_uuid
backend/app\tasks\context.py:124:        kwargs["correlation_id"] = correlation_id
backend/app\tasks\context.py:151:            return task_fn(self, *args, **kwargs)
backend/app\tasks\beat_schedule.py:40:            "kwargs": {"schedule_class": "minute"},
```

---

## 3. Runtime audit (real worker process; stdout/stderr captured)

### 3.1 Baseline (before remediation)

Worker command:
```powershell
cd backend
$env:PROMETHEUS_MULTIPROC_DIR="<abs_path>"
python -m celery -A app.celery_app.celery_app worker -P solo -c 1 -Q housekeeping --without-gossip --without-mingle --without-heartbeat --loglevel=INFO
```

Captured worker stdout:
```text
 
 -------------- celery@workstation v5.6.0 (recovery)
--- ***** ----- 
-- ******* ---- Windows-10-10.0.26100-SP0 2026-01-19 09:42:23
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         skeldir_backend:0x1fda00ee850
- ** ---------- .> transport:   sqla+postgresql://app_user:**@localhost:5432/skeldir_validation
- ** ---------- .> results:     postgresql://app_user:**@localhost:5432/skeldir_validation
- *** --- * --- .> concurrency: 1 (solo)
-- ******* ---- .> task events: ON
--- ***** ----- 
 -------------- [queues]
                .> housekeeping     exchange=tasks(direct) key=housekeeping.#
                

[tasks]
  . app.tasks.attribution.recompute_window
  . app.tasks.health.probe
  . app.tasks.housekeeping.ping
  . app.tasks.llm.budget_optimization
  . app.tasks.llm.explanation
  . app.tasks.llm.investigation
  . app.tasks.llm.route
  . app.tasks.maintenance.enforce_data_retention
  . app.tasks.maintenance.refresh_all_matviews_global_legacy
  . app.tasks.maintenance.refresh_matview_for_tenant
  . app.tasks.maintenance.scan_for_pii_contamination
  . app.tasks.matviews.pulse_matviews_global
  . app.tasks.matviews.refresh_all_for_tenant
  . app.tasks.matviews.refresh_single
  . app.tasks.r4_failure_semantics.crash_after_write_pre_ack
  . app.tasks.r4_failure_semantics.poison_pill
  . app.tasks.r4_failure_semantics.privilege_probes
  . app.tasks.r4_failure_semantics.rls_cross_tenant_probe
  . app.tasks.r4_failure_semantics.runaway_sleep
  . app.tasks.r4_failure_semantics.sentinel_side_effect
  . app.tasks.r6_resource_governance.pid_probe
  . app.tasks.r6_resource_governance.prefetch_long_task
  . app.tasks.r6_resource_governance.prefetch_short_task
  . app.tasks.r6_resource_governance.retry_probe
  . app.tasks.r6_resource_governance.runtime_snapshot
  . app.tasks.r6_resource_governance.timeout_probe
```

Captured worker stderr:
```text
{"level": "INFO", "logger": "app.celery_app", "message": "celery_worker_logging_configured"}
{"level": "INFO", "logger": "celery.worker.consumer.connection", "message": "Connected to sqla+postgresql://app_user:**@localhost:5432/skeldir_validation"}
{"level": "INFO", "logger": "app.celery_app", "message": "celery_worker_registered_tasks"}
{"level": "INFO", "logger": "app.celery_app", "message": "celery_kombu_visibility_recovery_started"}
{"level": "INFO", "logger": "celery.apps.worker", "message": "celery@workstation ready."}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[537a28e6-7218-4dba-af03-7afa680ba88e] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "537a28e6-7218-4dba-af03-7afa680ba88e", "correlation_id_request": "537a28e6-7218-4dba-af03-7afa680ba88e"}
{"level": "WARNING", "logger": "app.celery_app", "message": "celery_kombu_visibility_recovered_messages"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "537a28e6-7218-4dba-af03-7afa680ba88e", "db_user": "app_user", "correlation_id_request": "537a28e6-7218-4dba-af03-7afa680ba88e"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[537a28e6-7218-4dba-af03-7afa680ba88e] succeeded in 0.10899999999674037s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:23.990275+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[c212b8cd-f820-4709-8b0a-73eb4c3e7817] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "c212b8cd-f820-4709-8b0a-73eb4c3e7817", "correlation_id_request": "c212b8cd-f820-4709-8b0a-73eb4c3e7817"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "c212b8cd-f820-4709-8b0a-73eb4c3e7817", "db_user": "app_user", "correlation_id_request": "c212b8cd-f820-4709-8b0a-73eb4c3e7817"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[c212b8cd-f820-4709-8b0a-73eb4c3e7817] succeeded in 0.0940000000409782s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.098275+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[1224f114-84d7-4913-b07d-a994fb52e6c4] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "1224f114-84d7-4913-b07d-a994fb52e6c4", "correlation_id_request": "1224f114-84d7-4913-b07d-a994fb52e6c4"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "1224f114-84d7-4913-b07d-a994fb52e6c4", "db_user": "app_user", "correlation_id_request": "1224f114-84d7-4913-b07d-a994fb52e6c4"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[1224f114-84d7-4913-b07d-a994fb52e6c4] succeeded in 0.10899999999674037s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.208275+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[c8bb5005-9acb-46d6-8e88-ea5b1857a4af] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "c8bb5005-9acb-46d6-8e88-ea5b1857a4af", "correlation_id_request": "c8bb5005-9acb-46d6-8e88-ea5b1857a4af"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "c8bb5005-9acb-46d6-8e88-ea5b1857a4af", "db_user": "app_user", "correlation_id_request": "c8bb5005-9acb-46d6-8e88-ea5b1857a4af"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[c8bb5005-9acb-46d6-8e88-ea5b1857a4af] succeeded in 0.10999999998603016s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.316276+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[f99dc7b0-e220-47d7-a45e-909d9493dad1] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "f99dc7b0-e220-47d7-a45e-909d9493dad1", "correlation_id_request": "f99dc7b0-e220-47d7-a45e-909d9493dad1"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "f99dc7b0-e220-47d7-a45e-909d9493dad1", "db_user": "app_user", "correlation_id_request": "f99dc7b0-e220-47d7-a45e-909d9493dad1"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[f99dc7b0-e220-47d7-a45e-909d9493dad1] succeeded in 0.10899999999674037s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.425276+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[bea4f010-9823-4982-8101-6f3e659db7b8] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "bea4f010-9823-4982-8101-6f3e659db7b8", "correlation_id_request": "bea4f010-9823-4982-8101-6f3e659db7b8"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "bea4f010-9823-4982-8101-6f3e659db7b8", "db_user": "app_user", "correlation_id_request": "bea4f010-9823-4982-8101-6f3e659db7b8"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[bea4f010-9823-4982-8101-6f3e659db7b8] succeeded in 0.10899999999674037s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.530346+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[eeb16ab9-ccc8-40dd-8f94-3d328a305349] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "eeb16ab9-ccc8-40dd-8f94-3d328a305349", "correlation_id_request": "eeb16ab9-ccc8-40dd-8f94-3d328a305349"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "eeb16ab9-ccc8-40dd-8f94-3d328a305349", "db_user": "app_user", "correlation_id_request": "eeb16ab9-ccc8-40dd-8f94-3d328a305349"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[eeb16ab9-ccc8-40dd-8f94-3d328a305349] succeeded in 0.21899999998277053s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:24.638348+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[bb2bd301-8121-478b-a372-64f928050c8c] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "bb2bd301-8121-478b-a372-64f928050c8c", "correlation_id_request": "bb2bd301-8121-478b-a372-64f928050c8c"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_success", "task_name": "app.tasks.housekeeping.ping", "task_id": "bb2bd301-8121-478b-a372-64f928050c8c", "db_user": "app_user", "correlation_id_request": "bb2bd301-8121-478b-a372-64f928050c8c", "tenant_id": "00000000-0000-0000-0000-000000000000"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[bb2bd301-8121-478b-a372-64f928050c8c] succeeded in 0.10899999999674037s: {'status': 'ok', 'timestamp': '2026-01-19T15:42:35.914392+00:00', 'db_user': 'app_user', 'worker': 'celery@workstation'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.housekeeping.ping[d97aa0ee-dce3-49eb-b345-96fc0482f3d6] received"}
{"level": "INFO", "logger": "app.tasks.housekeeping", "message": "celery_task_start", "task_name": "app.tasks.housekeeping.ping", "task_id": "d97aa0ee-dce3-49eb-b345-96fc0482f3d6", "correlation_id_request": "d97aa0ee-dce3-49eb-b345-96fc0482f3d6"}
{"level": "ERROR", "logger": "app.celery_app", "message": "celery_task_failed", "task_name": "app.tasks.housekeeping.ping", "task_id": "d97aa0ee-dce3-49eb-b345-96fc0482f3d6"}
{"level": "ERROR", "logger": "celery.app.trace", "message": "Task app.tasks.housekeeping.ping[d97aa0ee-dce3-49eb-b345-96fc0482f3d6] raised unexpected: ValueError('ping failure requested')", "exc_info": "Traceback (most recent call last):\n  File \"C:\\Python311\\Lib\\site-packages\\celery\\app\\trace.py\", line 479, in trace_task\n    R = retval = fun(*args, **kwargs)\n                 ^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Python311\\Lib\\site-packages\\celery\\app\\trace.py\", line 779, in __protected_call__\n    return self.run(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\ayewhy\\II SKELDIR II\\backend\\app\\tasks\\housekeeping.py\", line 116, in ping\n    raise ValueError(\"ping failure requested\")\nValueError: ping failure requested"}
```

Baseline conclusion: JSON logs existed, but no canonical lifecycle schema and failure paths included unbounded tracebacks via Celery trace logger.

### 3.2 Remediated runtime proof (after remediation)

Config proof (eager mode disabled):
```text
﻿task_always_eager= False
```

Worker command:
```powershell
cd backend
$env:SKELDIR_TEST_TASKS="1"
$env:PROMETHEUS_MULTIPROC_DIR="<abs_path>"
python -m celery -A app.celery_app.celery_app worker -P solo -c 1 -Q housekeeping --without-gossip --without-mingle --without-heartbeat --loglevel=INFO
```

Captured worker stdout (includes success + failure lifecycle records):
```text
 
 -------------- celery@workstation v5.6.0 (recovery)
--- ***** ----- 
-- ******* ---- Windows-10-10.0.26100-SP0 2026-01-19 09:49:46
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         skeldir_backend:0x1e6dfb97e90
- ** ---------- .> transport:   sqla+postgresql://app_user:**@localhost:5432/skeldir_validation
- ** ---------- .> results:     postgresql://app_user:**@localhost:5432/skeldir_validation
- *** --- * --- .> concurrency: 1 (solo)
-- ******* ---- .> task events: ON
--- ***** ----- 
 -------------- [queues]
                .> housekeeping     exchange=tasks(direct) key=housekeeping.#
                

[tasks]
  . app.tasks.attribution.recompute_window
  . app.tasks.health.probe
  . app.tasks.housekeeping.ping
  . app.tasks.llm.budget_optimization
  . app.tasks.llm.explanation
  . app.tasks.llm.investigation
  . app.tasks.llm.route
  . app.tasks.maintenance.enforce_data_retention
  . app.tasks.maintenance.refresh_all_matviews_global_legacy
  . app.tasks.maintenance.refresh_matview_for_tenant
  . app.tasks.maintenance.scan_for_pii_contamination
  . app.tasks.matviews.pulse_matviews_global
  . app.tasks.matviews.refresh_all_for_tenant
  . app.tasks.matviews.refresh_single
  . app.tasks.observability_test.failure
  . app.tasks.observability_test.success
  . app.tasks.r4_failure_semantics.crash_after_write_pre_ack
  . app.tasks.r4_failure_semantics.poison_pill
  . app.tasks.r4_failure_semantics.privilege_probes
  . app.tasks.r4_failure_semantics.rls_cross_tenant_probe
  . app.tasks.r4_failure_semantics.runaway_sleep
  . app.tasks.r4_failure_semantics.sentinel_side_effect
  . app.tasks.r6_resource_governance.pid_probe
  . app.tasks.r6_resource_governance.prefetch_long_task
  . app.tasks.r6_resource_governance.prefetch_short_task
  . app.tasks.r6_resource_governance.retry_probe
  . app.tasks.r6_resource_governance.runtime_snapshot
  . app.tasks.r6_resource_governance.timeout_probe

{"tenant_id": "00000000-0000-0000-0000-000000000000", "correlation_id": "1579d6f8-a86e-4dca-a228-6419ac37ee7d", "task_name": "app.tasks.observability_test.success", "queue_name": "housekeeping", "status": "started", "error_type": null, "task_id": "3c06fe24-f142-4a39-babe-24723e661e4e"}
{"tenant_id": "00000000-0000-0000-0000-000000000000", "correlation_id": "1579d6f8-a86e-4dca-a228-6419ac37ee7d", "task_name": "app.tasks.observability_test.success", "queue_name": "housekeeping", "status": "success", "error_type": null, "task_id": "3c06fe24-f142-4a39-babe-24723e661e4e", "duration_ms": 83}
{"tenant_id": "00000000-0000-0000-0000-000000000000", "correlation_id": "85babe3f-91d7-4731-ab9d-eb2793831765", "task_name": "app.tasks.observability_test.failure", "queue_name": "housekeeping", "status": "started", "error_type": null, "task_id": "4e774615-be54-4510-ab3d-350295a00843"}
{"tenant_id": "00000000-0000-0000-0000-000000000000", "correlation_id": "85babe3f-91d7-4731-ab9d-eb2793831765", "task_name": "app.tasks.observability_test.failure", "queue_name": "housekeeping", "status": "failure", "error_type": "ValueError", "task_id": "4e774615-be54-4510-ab3d-350295a00843", "duration_ms": 77, "exc_message_trunc": "observability_test_failure", "retry": false, "retries": 0}
```

Captured worker stderr (Celery/system logs):
```text
{"level": "INFO", "logger": "app.celery_app", "message": "celery_worker_logging_configured"}
{"level": "INFO", "logger": "celery.worker.consumer.connection", "message": "Connected to sqla+postgresql://app_user:**@localhost:5432/skeldir_validation"}
{"level": "INFO", "logger": "app.celery_app", "message": "celery_worker_registered_tasks"}
{"level": "INFO", "logger": "app.celery_app", "message": "celery_kombu_visibility_recovery_started"}
{"level": "INFO", "logger": "celery.apps.worker", "message": "celery@workstation ready."}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.observability_test.success[3c06fe24-f142-4a39-babe-24723e661e4e] received"}
{"level": "INFO", "logger": "celery.app.trace", "message": "Task app.tasks.observability_test.success[3c06fe24-f142-4a39-babe-24723e661e4e] succeeded in 0.09399999998277053s: {'status': 'ok'}"}
{"level": "INFO", "logger": "celery.worker.strategy", "message": "Task app.tasks.observability_test.failure[4e774615-be54-4510-ab3d-350295a00843] received"}
{"level": "ERROR", "logger": "celery.app.trace", "message": "Task app.tasks.observability_test.failure[4e774615-be54-4510-ab3d-350295a00843] raised unexpected: ValueError('observability_test_failure')", "exc_info": "Traceback (most recent call last):\n  File \"C:\\Python311\\Lib\\site-packages\\celery\\app\\trace.py\", line 479, in trace_task\n    R = retval = fun(*args, **kwargs)\n                 ^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Python311\\Lib\\site-packages\\celery\\app\\trace.py\", line 779, in __protected_call__\n    return self.run(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\ayewhy\\II SKELDIR II\\backend\\app\\tasks\\observability_test.py\", line 22, in failure\n    raise ValueError(\"observability_test_failure\")\nValueError: observability_test_failure"}
```

---

## 4. Remediation implementation

### 4.1 Canonical lifecycle schema emitter
- `backend/app/observability/celery_task_lifecycle.py` emits allowlisted JSON lifecycle records via a dedicated raw-JSON logger.
- Deterministic context precedence is implemented exactly as required (contextvars ? kwargs ? task.request ? "unknown" + separate warning).

### 4.2 Universal emission via Celery signals
- `backend/app/celery_app.py` wires lifecycle emission at `task_prerun` (started), `task_success` (success), `task_failure` (failure), and `task_retry` (retry-as-failure with `retry=true`).

### 4.3 Test-only tasks for deterministic success/failure
- `backend/app/tasks/observability_test.py` provides DB-free tasks, loaded only when `SKELDIR_TEST_TASKS=1`.

---

## 5. CI-enforced test (subprocess worker; JSON parsing; anti-eager)

Test file:
- `backend/tests/test_b0566_structured_worker_logging_runtime.py`

How it runs:
```powershell
pytest -q backend/tests/test_b0566_structured_worker_logging_runtime.py
```

What it asserts:
- Starts a real Celery worker subprocess (prefork on POSIX; solo on Windows).
- Sends deterministic success + failure tasks.
- Parses emitted JSON from worker output and asserts required keys + allowlist (no args/kwargs/payload/token/secret/Authorization).
- Asserts eager mode is disabled (`celery_app.conf.task_always_eager is False`).

---

## 6. Exit gates (EG6.1?EG6.5)

- **EG6.1 (Success schema proof)**: met by ?3.2 stdout lifecycle record with `status="success"` and test assertions.
- **EG6.2 (Failure schema proof)**: met by ?3.2 stdout lifecycle record with `status="failure"` and non-empty `error_type`, and test assertions.
- **EG6.3 (Runtime-based; anti-eager)**: met by worker subprocess test + `runtime_config_proof.txt` showing eager disabled.
- **EG6.4 (Payload/PII non-leak guard)**: met by allowlist enforcement in code + negative assertions in the subprocess test.
- **EG6.5 (Ledger/provenance closure)**: met by this evidence pack + `docs/forensics/INDEX.md` row update; CI run URL pending.

---

## 7. Provenance

- Commit: 11fb434c5b485e63d91dcb312cb6baa401494b86
- CI run: pending
