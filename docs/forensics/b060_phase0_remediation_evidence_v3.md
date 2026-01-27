# b060_phase0_remediation_evidence_v3

```text
$ git rev-parse HEAD
57b0007992392d3883a532c5cb23aca4d043a370
```

```text
$ git status -sb
## main...origin/main
?? docs/forensics/b060_phase0_remediation_evidence_v3.md
```

```text
$ rg -n -C 8 required: api-contracts/openapi/v1/revenue.yaml
58-          $ref: './_common/base.yaml#/components/responses/RateLimitError'
59-        '500':
60-          $ref: './_common/base.yaml#/components/responses/ServerError'
61-
62-components:
63-  schemas:
64-    RealtimeRevenueV1Response:
65-      type: object
66:      required:
67-        - tenant_id
68-        - interval
69-        - currency
70-        - revenue_total
71-        - verified
72-        - data_as_of
73-      properties:
74-        tenant_id:
```

```text
$ rg -n -C 3 data_as_of api-contracts/openapi/v1/revenue.yaml
50-                currency: USD
51-                revenue_total: 125430.50
52-                verified: false
53:                data_as_of: '2026-01-26T12:00:00Z'
54-                sources: []
55-        '401':
56-          $ref: './_common/base.yaml#/components/responses/UnauthorizedError'
--
69-        - currency
70-        - revenue_total
71-        - verified
72:        - data_as_of
73-      properties:
74-        tenant_id:
75-          type: string
--
97-          type: boolean
98-          description: Whether revenue is verified through payment reconciliation
99-          example: false
100:        data_as_of:
101-          type: string
102-          format: date-time
103-          description: Timestamp of last successful upstream fetch
```

```text
$ gh run view 21381109187

? main CI · 21381109187
Triggered via push about 6 minutes ago

JOBS
? Checkout Code in 10s (ID 61548364671)
? Validate Phase Manifest in 12s (ID 61548379515)
? Governance Guardrails in 21s (ID 61548379517)
? Validate Contracts in 1m42s (ID 61548379518)
? Zero-Drift v3.2 CI Truth Layer in 1m29s (ID 61548379523)
? Frontend E2E (Playwright) in 34s (ID 61548379541)
? B0.5.3.3 Revenue Contract Tests in 1m27s (ID 61548379543)
? B0.5.7 P6 E2E (Least-Privilege) in 1m18s (ID 61548379546)
? Backend Integration (B0567) in 1m30s (ID 61548379554)
? Celery Foundation B0.5.1 in 1m53s (ID 61548379555)
? Validate Migrations in 9s (ID 61548379557)
- Test Frontend (ID 61548379599)
- Generate Pydantic Models (ID 61548379646)
- Test Backend (ID 61548379711)
? Phase Chain (B0.4 target) in 3m7s (ID 61548395052)
? Phase Gates (VALUE_02) in 2m19s (ID 61548395076)
? Phase Gates (B0.4) in 2m13s (ID 61548395080)
? Phase Gates (VALUE_05) in 2m8s (ID 61548395081)
? Phase Gates (B0.2) in 2m51s (ID 61548395086)
? Phase Gates (VALUE_01) in 2m8s (ID 61548395090)
? Phase Gates (VALUE_03) in 2m12s (ID 61548395091)
? Phase Gates (B0.1) in 2m52s (ID 61548395096)
? Phase Gates (VALUE_04) in 2m24s (ID 61548395097)
? Phase Gates (SCHEMA_GUARD) in 2m5s (ID 61548395109)
? Phase Gates (B0.3) in 2m3s (ID 61548395114)
? Proof Pack (EG-5) in 12s (ID 61548570121)

ANNOTATIONS
! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Validate Contracts: .github#18

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Chain (B0.4 target): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (VALUE_02): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (B0.4): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (VALUE_05): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (B0.2): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (VALUE_01): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (VALUE_03): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (B0.1): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (VALUE_04): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (SCHEMA_GUARD): .github#28

! Restore cache failed: Dependencies file is not found in /home/runner/work/skeldir-2.0/skeldir-2.0. Supported file pattern: go.sum
Phase Gates (B0.3): .github#28


ARTIFACTS
b057-p6-full-chain-artifacts
b0562-health-probe-logs-57b0007992392d3883a532c5cb23aca4d043a370
b055-evidence-bundle-57b0007992392d3883a532c5cb23aca4d043a370
phase-B0.3-evidence
phase-SCHEMA_GUARD-evidence
phase-VALUE_01-evidence
phase-VALUE_05-evidence
phase-VALUE_03-evidence
phase-B0.4-evidence
phase-VALUE_02-evidence
phase-VALUE_04-evidence
phase-B0.2-evidence
phase-B0.1-evidence
phase-chain-evidence
value-trace-proof-pack

For more information about a job, try: gh run view --job=<job-id>
View this run on GitHub: https://github.com/Muk223/skeldir-2.0/actions/runs/21381109187
```

```text
$ gh run view --job 61548379543 --log | rg -n -C 3 test_b06_realtime_revenue_v1.py
1424-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5606298Z [36;1m[0m
1425-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5606638Z [36;1mexport DATABASE_URL="$DATABASE_URL_ASYNC"[0m
1426-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5607278Z [36;1mpytest tests/test_b0533_revenue_input_contract.py -v --tb=short[0m
1427:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5608021Z [36;1mpytest tests/test_b06_realtime_revenue_v1.py -v --tb=short[0m
1428-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5608761Z [36;1mpytest ../tests/contract/test_contract_semantics.py -v --tb=short[0m
1429-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5609336Z [36;1m[0m
1430-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5609989Z [36;1mecho "? R5-5 MET / G5 PASSED: Contract tests executed (see pytest output above for pass/fail status)"[0m
--
1517-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:32.4161217Z asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
1518-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:32.8805930Z collecting ... collected 2 items
1519-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:32.8806375Z 
1520:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.0976523Z tests/test_b06_realtime_revenue_v1.py::test_realtime_revenue_v1_response_shape 
1521-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.0977589Z -------------------------------- live log call ---------------------------------
1522-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.0978600Z INFO     httpx:_client.py:1740 HTTP Request: GET http://test/api/v1/revenue/realtime "HTTP/1.1 200 OK"
1523-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.0993547Z PASSED                                                                   [ 50%]
1524:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.1016954Z tests/test_b06_realtime_revenue_v1.py::test_realtime_revenue_v1_requires_authorization 
1525-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.1018239Z -------------------------------- live log call ---------------------------------
1526-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.1019277Z INFO     httpx:_client.py:1740 HTTP Request: GET http://test/api/v1/revenue/realtime "HTTP/1.1 401 Unauthorized"
1527-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:33.4302962Z PASSED                                                                   [100%]
```

```text
$ gh run view --job 61548379543 --log | rg -n -C 3 test_contract_semantics.py
1425-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5606638Z [36;1mexport DATABASE_URL="$DATABASE_URL_ASYNC"[0m
1426-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5607278Z [36;1mpytest tests/test_b0533_revenue_input_contract.py -v --tb=short[0m
1427-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5608021Z [36;1mpytest tests/test_b06_realtime_revenue_v1.py -v --tb=short[0m
1428:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5608761Z [36;1mpytest ../tests/contract/test_contract_semantics.py -v --tb=short[0m
1429-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5609336Z [36;1m[0m
1430-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5609989Z [36;1mecho "? R5-5 MET / G5 PASSED: Contract tests executed (see pytest output above for pass/fail status)"[0m
1431-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:27.5650592Z shell: /usr/bin/bash -e {0}
--
1542-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:34.1998859Z asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
1543-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.1225405Z collecting ... collected 16 items
1544-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.1225909Z 
1545:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7221858Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[reconciliation.bundled.yaml] SKIPPED [  6%]
1546:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7281706Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[webhooks.stripe.bundled.yaml] SKIPPED [ 12%]
1547:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7340924Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[webhooks.woocommerce.bundled.yaml] SKIPPED [ 18%]
1548:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7399450Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[attribution.bundled.yaml] SKIPPED [ 25%]
1549:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7447923Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[webhooks.paypal.bundled.yaml] SKIPPED [ 31%]
1550:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7496682Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[llm-investigations.bundled.yaml] SKIPPED [ 37%]
1551:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:35.7536110Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[revenue.bundled.yaml] SKIPPED [ 43%]
1552:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5189875Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[auth.bundled.yaml] 
1553-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5191136Z -------------------------------- live log call ---------------------------------
1554-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5192266Z INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/auth/login "HTTP/1.1 200 OK"
1555-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5545243Z PASSED                                                                   [ 50%]
1556:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5807249Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[health.bundled.yaml] 
1557-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5808378Z -------------------------------- live log call ---------------------------------
1558-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5809325Z INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/health "HTTP/1.1 404 Not Found"
1559-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5894946Z INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/health/ready "HTTP/1.1 404 Not Found"
1560-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.5982390Z INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/health/live "HTTP/1.1 404 Not Found"
1561-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6003615Z SKIPPED (All operations returned 404 (not implemented) in health.bun...) [ 56%]
1562:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6051510Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[llm-budget.bundled.yaml] SKIPPED [ 62%]
1563:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6108953Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[webhooks.shopify.bundled.yaml] SKIPPED [ 68%]
1564:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6156598Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[export.bundled.yaml] SKIPPED [ 75%]
1565:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6198901Z ../tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[llm-explanations.bundled.yaml] SKIPPED [ 81%]
1566:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6241785Z ../tests/contract/test_contract_semantics.py::test_auth_login_happy_path 
1567-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6242727Z -------------------------------- live log call ---------------------------------
1568-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6243687Z INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/auth/login "HTTP/1.1 200 OK"
1569-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6251119Z PASSED                                                                   [ 87%]
1570:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6291125Z ../tests/contract/test_contract_semantics.py::test_attribution_revenue_realtime_happy_path 
1571-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6292098Z -------------------------------- live log call ---------------------------------
1572-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6293150Z INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/attribution/revenue/realtime "HTTP/1.1 200 OK"
1573-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6299625Z PASSED                                                                   [ 93%]
1574:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6357734Z ../tests/contract/test_contract_semantics.py::test_coverage_report PASSED [100%]
1575-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6358417Z 
1576-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6358656Z =============================== warnings summary ===============================
1577-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6359189Z <string>:1: 136 warnings
1578-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6361069Z   <string>:1: PydanticDeprecatedSince20: Using extra keyword arguments on `Field` is deprecated and will be removed. Use `json_schema_extra` instead. (Extra keys: 'example'). Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
1579-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6362838Z 
1580:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6363318Z tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[auth.bundled.yaml]
1581:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6366357Z   /home/runner/work/skeldir-2.0/skeldir-2.0/tests/contract/test_contract_semantics.py:96: NonInteractiveExampleWarning: The `.example()` method is good for exploring strategies, but should only be used interactively.  We recommend using `@given` for tests - it performs better, saves and replays failures to avoid flakiness, and reports minimal examples. (strategy: openapi_cases(operation=APIOperation(path='/api/auth/login',
1582-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6368882Z    method='post',
1583-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6369156Z    definition=,
1584-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6369390Z    schema=,
--
1719-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6445984Z    body=)))
1720-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6446264Z     case = operation.as_strategy().example()
1721-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6446541Z 
1722:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6446977Z tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[health.bundled.yaml]
1723:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6449669Z   /home/runner/work/skeldir-2.0/skeldir-2.0/tests/contract/test_contract_semantics.py:96: NonInteractiveExampleWarning: The `.example()` method is good for exploring strategies, but should only be used interactively.  We recommend using `@given` for tests - it performs better, saves and replays failures to avoid flakiness, and reports minimal examples. (strategy: openapi_cases(operation=APIOperation(path='/api/health',
1724-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6452039Z    method='get',
1725-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6452286Z    definition=,
1726-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6452531Z    schema=,
--
1822-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6503200Z    body=)))
1823-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6503462Z     case = operation.as_strategy().example()
1824-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6503723Z 
1825:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6504168Z tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[health.bundled.yaml]
1826:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6506870Z   /home/runner/work/skeldir-2.0/skeldir-2.0/tests/contract/test_contract_semantics.py:96: NonInteractiveExampleWarning: The `.example()` method is good for exploring strategies, but should only be used interactively.  We recommend using `@given` for tests - it performs better, saves and replays failures to avoid flakiness, and reports minimal examples. (strategy: openapi_cases(operation=APIOperation(path='/api/health/ready',
1827-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6509335Z    method='get',
1828-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6509588Z    definition=,
1829-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6509829Z    schema=,
--
1897-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:37.6548579Z    body=)))
1898-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0185661Z     case = operation.as_strategy().example()
1899-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0186233Z 
1900:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0187070Z tests/contract/test_contract_semantics.py::test_contract_semantic_conformance[health.bundled.yaml]
1901:B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0190062Z   /home/runner/work/skeldir-2.0/skeldir-2.0/tests/contract/test_contract_semantics.py:96: NonInteractiveExampleWarning: The `.example()` method is good for exploring strategies, but should only be used interactively.  We recommend using `@given` for tests - it performs better, saves and replays failures to avoid flakiness, and reports minimal examples. (strategy: openapi_cases(operation=APIOperation(path='/api/health/live',
1902-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0192624Z    method='get',
1903-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0192903Z    definition=,
1904-B0.5.3.3 Revenue Contract Tests	R5-5 / Gate G5 - Run B0.5.3.3 contract tests (2 tests must pass)	2026-01-27T01:44:38.0193175Z    schema=,
```

