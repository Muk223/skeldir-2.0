# Dynamic Conformance: Negative Test Scenarios

This document describes negative test scenarios that prove the dynamic conformance checker (Schemathesis) correctly detects and prevents runtime behavior divergence from OpenAPI contracts.

**Purpose**: These tests empirically validate that behavioral drift (status codes, response schemas) is caught even when static structure aligns.

## Test Execution Instructions

Each scenario should be tested on a separate branch. The expected result is **test failure** with Schemathesis validation errors.

---

## Scenario 1: Wrong Status Code (201 vs 200)

**Objective**: Prove that returning a different status code than specified in the contract causes dynamic conformance tests to fail.

### Test Steps:

1. Create test branch: `git checkout -b test/wrong-status-code`

2. Modify `backend/app/api/auth.py` to return 201 instead of 200:

```python
@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=201,  # Changed from 200 - contract specifies 200
    operation_id="login",
    ...
)
async def login(...):
    return LoginResponse(...)
```

3. Run dynamic conformance tests:
```bash
cd tests/contract
pytest test_contract_semantics.py -v
```

### Expected Result:

```
FAILED test_contract_semantics.py::test_contract_semantic_conformance[auth.bundled.yaml]

Schemathesis validation error:
  Response status code 201 is not defined in the schema for POST /api/auth/login
  Allowed status codes: [200, 401, 429, 500]
  
Exit Code: 1
```

### Forensic Validation:

- ✓ Status code mismatch detected by Schemathesis
- ✓ Test fails with clear error message
- ✓ Expected status codes listed in error
- ✓ CI pipeline would block merge

---

## Scenario 2: Missing Required Response Field

**Objective**: Prove that omitting a required field from the response causes schema validation failure.

### Test Steps:

1. Create test branch: `git checkout -b test/missing-field`

2. Modify `backend/app/api/attribution.py` to omit `verified` field:

```python
@router.get(
    "/revenue/realtime",
    response_model=RealtimeRevenueResponse,
    ...
)
async def get_realtime_revenue(...):
    return RealtimeRevenueResponse(
        total_revenue="125000.50",
        # verified=True,  # OMITTED - required by contract
        data_freshness_seconds=45,
        tenant_id=uuid4()
    )
```

Note: This will actually fail at Pydantic validation level before reaching Schemathesis. To bypass Pydantic:

```python
# Return dict instead of model to bypass Pydantic
@router.get("/revenue/realtime")
async def get_realtime_revenue(...):
    return {
        "total_revenue": "125000.50",
        # "verified" missing
        "data_freshness_seconds": 45,
        "tenant_id": str(uuid4())
    }
```

3. Run tests:
```bash
pytest tests/contract/test_contract_semantics.py::test_attribution_revenue_realtime_happy_path -v
```

### Expected Result:

```
FAILED test_attribution_revenue_realtime_happy_path

AssertionError: Missing verified in response

OR (if using Schemathesis):

Schemathesis schema validation error:
  Response body does not match schema for GET /api/attribution/revenue/realtime
  Missing required property: 'verified'
  
Exit Code: 1
```

### Forensic Validation:

- ✓ Missing required field detected
- ✓ Test fails with clear error message
- ✓ Schema validation catches structural deviation
- ✓ CI pipeline would block merge

---

## Scenario 3: Wrong Field Type

**Objective**: Prove that returning wrong field types causes schema validation failure.

### Test Steps:

1. Create test branch: `git checkout -b test/wrong-field-type`

2. Modify `backend/app/api/attribution.py` to return wrong type:

```python
@router.get("/revenue/realtime")
async def get_realtime_revenue(...):
    return {
        "total_revenue": 125000.50,  # Should be string, returning number
        "verified": True,
        "data_freshness_seconds": 45,
        "tenant_id": str(uuid4())
    }
```

3. Run tests:
```bash
pytest tests/contract/test_contract_semantics.py -v
```

### Expected Result:

```
Schemathesis schema validation error:
  Response body does not match schema for GET /api/attribution/revenue/realtime
  Property 'total_revenue': type mismatch
    Expected: string
    Received: number
    
Exit Code: 1
```

### Forensic Validation:

- ✓ Type mismatch detected
- ✓ Test fails with clear error message
- ✓ Schema enforces type constraints
- ✓ CI pipeline would block merge

---

## Scenario 4: Non-RFC7807 Error Response

**Objective**: Prove that returning non-standard error format on 4xx/5xx causes schema validation failure.

### Test Steps:

1. Create test branch: `git checkout -b test/invalid-error-format`

2. Modify `backend/app/api/auth.py` to return custom error format:

```python
from fastapi import HTTPException

@router.post("/login", ...)
async def login(...):
    # Return non-RFC7807 error instead of standard Problem schema
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"  # Plain string, not Problem object
    )
```

3. Run tests with invalid credentials trigger:
```bash
pytest tests/contract/test_contract_semantics.py -v
```

### Expected Result:

```
Schemathesis schema validation error:
  Response body for status 401 does not match schema
  Expected RFC7807 Problem schema with properties: type, title, status, detail, instance
  Received: {"detail": "Invalid credentials"}
  
Exit Code: 1
```

### Forensic Validation:

- ✓ Non-standard error format detected
- ✓ Test fails with schema mismatch
- ✓ RFC7807 Problem schema enforced
- ✓ CI pipeline would block merge

---

## Scenario 5: Extra Undocumented Fields

**Objective**: Prove that returning extra fields not in contract causes validation failure (if additionalProperties: false).

### Test Steps:

1. Create test branch: `git checkout -b test/extra-fields`

2. Modify `backend/app/api/attribution.py` to include extra field:

```python
@router.get("/revenue/realtime")
async def get_realtime_revenue(...):
    return {
        "total_revenue": "125000.50",
        "verified": True,
        "data_freshness_seconds": 45,
        "tenant_id": str(uuid4()),
        "extra_undocumented_field": "surprise!"  # Not in contract
    }
```

3. Run tests:
```bash
pytest tests/contract/test_contract_semantics.py -v
```

### Expected Result:

```
Schemathesis schema validation error (if additionalProperties: false):
  Response body contains undocumented property: 'extra_undocumented_field'
  Schema does not allow additional properties
  
Exit Code: 1
```

**Note**: This only fails if OpenAPI schema has `additionalProperties: false`. Otherwise, extra fields are allowed by default.

### Forensic Validation:

- ✓ Extra fields detected (if schema configured)
- ✓ Test fails if additionalProperties: false
- ✓ Schema completeness enforced
- ✓ CI pipeline would block merge

---

## Scenario 6: Missing Required Headers

**Objective**: Prove that omitting required headers causes validation failure.

### Test Steps:

1. Create test branch: `git checkout -b test/missing-header`

2. Modify test to omit X-Correlation-ID header:

```python
def test_auth_login_without_correlation_id():
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "pass"},
        # headers={"X-Correlation-ID": str(uuid.uuid4())}  # OMITTED
    )
    
    # Contract requires X-Correlation-ID, should fail
    assert response.status_code == 422  # FastAPI validation error
```

3. Run test:
```bash
pytest tests/contract/test_contract_semantics.py -v
```

### Expected Result:

```
Response status code: 422 Unprocessable Entity
Validation error: Missing required header: X-Correlation-ID

Exit Code: 0 (test passes because it expects 422)
```

### Forensic Validation:

- ✓ Missing required header detected by FastAPI
- ✓ 422 status returned for validation errors
- ✓ Contract-defined requirements enforced
- ✓ Runtime validation prevents incomplete requests

---

## Test Execution Summary

To validate the entire dynamic conformance enforcement system:

```bash
# Run all contract semantic tests
cd tests/contract
pytest test_contract_semantics.py -v

# For each negative scenario above:
git checkout -b test/scenario-name
# Make the specified changes
pytest test_contract_semantics.py -v
# Verify test failure with clear diagnostic
git checkout main
git branch -D test/scenario-name
```

## Success Criteria

Dynamic conformance enforcement is considered empirically validated when:

- ✓ All 6 negative test scenarios produce test failures
- ✓ Each failure includes clear Schemathesis validation errors
- ✓ Status code deviations are caught
- ✓ Schema violations (missing fields, wrong types) are caught
- ✓ Error format compliance (RFC7807) is enforced
- ✓ Required parameters (headers, query params) are validated

## Coverage Verification

Run coverage report to ensure all operations tested:

```bash
pytest tests/contract/test_contract_semantics.py::test_coverage_report -v -s
```

Expected output:
```
Contract Coverage Report:
  Total in-scope routes: 4
  Routes:
    - POST /api/auth/login
    - POST /api/auth/refresh
    - POST /api/auth/logout
    - GET /api/attribution/revenue/realtime
```

## Integration with CI

These scenarios should be automated in CI to ensure:
1. Dynamic conformance tests don't break
2. Schemathesis integration remains functional
3. Runtime behavior stays aligned with contracts

See `.github/workflows/contract-enforcement.yml` for automation.



