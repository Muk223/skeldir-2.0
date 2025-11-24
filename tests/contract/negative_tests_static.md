# Static Conformance: Negative Test Scenarios

This document describes negative test scenarios that prove the static conformance checker correctly detects and prevents contract-implementation divergence.

**Purpose**: These tests empirically validate that the enforcement mechanism works by demonstrating CI failures for each divergence type.

## Test Execution Instructions

Each scenario should be tested on a separate branch to avoid contaminating main. The expected result is **CI failure** with specific diagnostic messages.

---

## Scenario 1: Undeclared Route (Implementation > Contract)

**Objective**: Prove that adding a FastAPI route without updating the contract causes static conformance check to fail.

### Test Steps:

1. Create test branch: `git checkout -b test/undeclared-route`

2. Add undeclared route to `backend/app/api/auth.py`:

```python
@router.post(
    "/test/undeclared",
    status_code=200,
    summary="Test undeclared endpoint"
)
async def test_undeclared():
    """This route has no corresponding OpenAPI contract."""
    return {"status": "undeclared"}
```

3. Run static conformance check:
```bash
python scripts/contracts/dump_routes.py
python scripts/contracts/check_static_conformance.py
```

### Expected Result:

```
✗ FAIL: Found 1 undeclared implementation route(s)

These routes exist in FastAPI but have no corresponding OpenAPI contract:
  POST   /api/auth/test/undeclared
         Operation ID: test_undeclared
         Source: test_undeclared

ACTION REQUIRED: Either:
  1. Add OpenAPI contract for these routes, OR
  2. Remove these routes from implementation, OR
  3. Mark as out-of-scope in contract_scope.yaml (if they're internal)

Exit Code: 1
```

### Forensic Validation:

- ✓ Undeclared route detected in R_only set
- ✓ Check fails with exit code 1
- ✓ Diagnostic message identifies exact route and action required
- ✓ CI pipeline would block merge

---

## Scenario 2: Phantom Contract Operation (Contract > Implementation)

**Objective**: Prove that removing a FastAPI route while leaving the contract intact causes static conformance check to fail.

### Test Steps:

1. Create test branch: `git checkout -b test/phantom-operation`

2. Comment out or delete the `/refresh` route in `backend/app/api/auth.py`:

```python
# @router.post(
#     "/refresh",
#     response_model=RefreshResponse,
#     ...
# )
# async def refresh_token(...):
#     ...
```

3. Run static conformance check:
```bash
python scripts/contracts/dump_routes.py
python scripts/contracts/check_static_conformance.py
```

### Expected Result:

```
✗ FAIL: Found 1 unimplemented contract operation(s)

These operations are defined in OpenAPI but not implemented in FastAPI:
  POST   /api/auth/refresh
         Operation ID: refreshToken
         Source: auth.bundled.yaml

ACTION REQUIRED: Either:
  1. Implement these operations in FastAPI, OR
  2. Remove from OpenAPI contracts, OR
  3. Add to contract_only_allowlist (if they're upcoming features)

Exit Code: 1
```

### Forensic Validation:

- ✓ Phantom operation detected in C_only set
- ✓ Check fails with exit code 1
- ✓ Diagnostic message identifies exact operation and action required
- ✓ CI pipeline would block merge

---

## Scenario 3: Path Parameter Mismatch

**Objective**: Prove that renaming a path parameter in implementation without updating the contract causes parameter consistency check to fail.

### Test Steps:

1. Create test branch: `git checkout -b test/path-param-mismatch`

2. Add a parameterized route with mismatched parameter name:

In `backend/app/api/auth.py`:
```python
@router.get(
    "/users/{user_id}",  # Implementation uses user_id
    status_code=200
)
async def get_user(user_id: str):
    return {"user_id": user_id}
```

In `api-contracts/openapi/v1/auth.yaml` (add operation):
```yaml
/api/auth/users/{id}:  # Contract uses id
  get:
    operationId: getUser
    parameters:
      - name: id  # Mismatch: contract says 'id', implementation says 'user_id'
        in: path
        required: true
        schema:
          type: string
```

3. Rebuild bundles and run conformance check:
```bash
cd api-contracts && npx @redocly/cli bundle auth --output=dist/openapi/v1/auth.bundled.yaml --force
python scripts/contracts/dump_routes.py
python scripts/contracts/dump_contract_ops.py
python scripts/contracts/check_static_conformance.py
```

### Expected Result:

```
✗ FAIL: Found 1 parameter mismatch(es)

  GET    /api/auth/users/{user_id}
         Mismatch Type: path_params
         Implementation: ['user_id']
         Contract: ['id']
         Missing in Impl: ['id']
         Missing in Contract: ['user_id']

ACTION REQUIRED: Align parameter names between implementation and contract

Exit Code: 1
```

### Forensic Validation:

- ✓ Parameter mismatch detected
- ✓ Check fails with exit code 1
- ✓ Diagnostic shows exact parameter names in each source
- ✓ CI pipeline would block merge

---

## Scenario 4: Query Parameter Mismatch

**Objective**: Prove that mismatched query parameter names are detected.

### Test Steps:

1. Create test branch: `git checkout -b test/query-param-mismatch`

2. Add route with query param in implementation:

In `backend/app/api/attribution.py`:
```python
from fastapi import Query

@router.get("/revenue/filtered")
async def get_filtered_revenue(
    cursor: str = Query(None, description="Pagination cursor")  # Implementation uses 'cursor'
):
    return {"cursor": cursor}
```

3. Add corresponding contract operation with different query param name:

In `api-contracts/openapi/v1/attribution.yaml`:
```yaml
/api/attribution/revenue/filtered:
  get:
    operationId: getFilteredRevenue
    parameters:
      - name: page  # Contract uses 'page', implementation uses 'cursor'
        in: query
        schema:
          type: string
```

4. Rebuild and check:
```bash
cd api-contracts && npx @redocly/cli bundle attribution --output=dist/openapi/v1/attribution.bundled.yaml --force
python scripts/contracts/dump_routes.py
python scripts/contracts/dump_contract_ops.py
python scripts/contracts/check_static_conformance.py
```

### Expected Result:

```
✗ FAIL: Found 1 parameter mismatch(es)

  GET    /api/attribution/revenue/filtered
         Mismatch Type: query_params
         Implementation: ['cursor']
         Contract: ['page']
         Missing in Impl: ['page']
         Missing in Contract: ['cursor']

Exit Code: 1
```

### Forensic Validation:

- ✓ Query parameter name mismatch detected
- ✓ Check fails with exit code 1
- ✓ Clear diagnostic of mismatch
- ✓ CI pipeline would block merge

---

## Test Execution Summary

To validate the entire static conformance enforcement system:

```bash
# For each scenario above:
git checkout -b test/scenario-name
# Make the specified changes
python scripts/contracts/dump_routes.py
python scripts/contracts/dump_contract_ops.py
python scripts/contracts/check_static_conformance.py
# Verify exit code is 1 and diagnostic message is clear
echo "Exit code: $?"
git checkout main
git branch -D test/scenario-name
```

## Success Criteria

Static conformance enforcement is considered empirically validated when:

- ✓ All 4 negative test scenarios produce CI failures
- ✓ Each failure includes clear diagnostic messages
- ✓ Exit codes are correct (1 for failure, 0 for pass)
- ✓ No false negatives (legitimate divergence must be caught)
- ✓ No false positives (aligned routes must pass)

## Integration with CI

These scenarios should be automated in CI test suite to ensure:
1. The enforcement mechanism itself doesn't break
2. New team members understand the failure modes
3. Documentation stays aligned with actual behavior

See `.github/workflows/contract-enforcement.yml` for automated execution.



