# Contract-First Enforcement: Implementation Guide

**Version**: 1.0  
**Status**: Operational  
**Last Updated**: Implementation Complete

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [System Components](#system-components)
4. [Development Workflow](#development-workflow)
5. [CI/CD Integration](#cicd-integration)
6. [Maintenance & Operations](#maintenance--operations)
7. [Troubleshooting](#troubleshooting)
8. [References](#references)

---

## Executive Summary

### What is Contract-First Enforcement?

Contract-first enforcement is an automated system that prevents FastAPI implementation from diverging from OpenAPI contracts through:

- **Static conformance checks**: Structural alignment (routes, parameters)
- **Dynamic conformance tests**: Behavioral validation (status codes, schemas)
- **CI/CD gates**: Automated blocking of divergent changes

### Key Benefits

- ✅ **Prevents API drift**: Impossible to deploy routes without contracts
- ✅ **Automated enforcement**: No manual reviews needed
- ✅ **Fast feedback**: Divergence caught in seconds during CI
- ✅ **Clear diagnostics**: Precise error messages guide fixes
- ✅ **Zero bypass**: Contract-first is architectural, not aspirational

### System Property

> **"Operational ≠ Functional" Invariant**  
> The system cannot be green (CI passing) while diverged (implementation ≠ contract)

---

## Architecture Overview

### Enforcement Triangle

```
       ┌─────────────────┐
       │   OpenAPI       │
       │   Contracts     │
       │  (Source of     │
       │    Truth)       │
       └────────┬────────┘
                │
                │ Bundling
                │
       ┌────────▼────────┐
       │   Bundled       │
       │   Specs         │
       └────┬───────┬────┘
            │       │
  Generation│       │Parsing
            │       │
    ┌───────▼──┐ ┌─▼───────┐
    │ Pydantic │ │ C-Graph │
    │  Models  │ │Contract │
    │          │ │  Ops    │
    └────┬─────┘ └─────┬───┘
         │             │
    Usage│             │Compare
         │             │
    ┌────▼─────┐   ┌───▼───────┐
    │ FastAPI  ├───► R-Graph   │
    │  Routes  │   │Impl Routes│
    └──────────┘   └───┬───────┘
                       │
                       │ Static Check
                       │
                  ┌────▼─────────┐
                  │ Conformance  │
                  │   Status     │
                  └──────────────┘
```

### Layers of Defense

1. **Scope Layer**: Machine-readable classification of all routes
2. **Static Layer**: Bidirectional route ↔ operation equivalence
3. **Dynamic Layer**: Runtime behavior validation via Schemathesis
4. **CI Layer**: Automated enforcement blocking non-conforming changes

---

## System Components

### 1. Scope Configuration

**File**: `backend/app/config/contract_scope.yaml`

**Purpose**: Define governance boundary - which routes are governed by contracts

**Structure**:
```yaml
in_scope_prefixes:
  - /api/auth
  - /api/attribution
  # Routes under these prefixes MUST have contracts

out_of_scope_paths:
  - /health
  - /docs
  # These routes explicitly excluded from enforcement

contract_only_allowlist:
  # Operations in contracts but not yet implemented
  # Use sparingly - for upcoming features only
  []

spec_mappings:
  /api/auth: api-contracts/dist/openapi/v1/auth.bundled.yaml
  # Maps prefixes to their OpenAPI specs
```

**When to Update**:
- Adding new API domain (add to `in_scope_prefixes` and `spec_mappings`)
- Adding internal routes (add pattern to `out_of_scope_paths`)
- Planning future endpoints (add to `contract_only_allowlist` temporarily)

---

### 2. Route Introspection (R-Graph)

**Script**: `scripts/contracts/dump_routes.py`

**Purpose**: Generate canonical representation of FastAPI implementation routes

**Output**: `tmp/r_graph.json`

**Example Entry**:
```json
{
  "method": "POST",
  "path": "/api/auth/login",
  "operation_id": "login",
  "request_model": "LoginRequest",
  "response_model": "LoginResponse",
  "path_params": [],
  "query_params": []
}
```

**Usage**:
```bash
python scripts/contracts/dump_routes.py
```

**Exit Codes**:
- `0`: R-Graph generated successfully
- `1`: FastAPI app cannot be imported or error occurred

---

### 3. Contract Introspection (C-Graph)

**Script**: `scripts/contracts/dump_contract_ops.py`

**Purpose**: Generate canonical representation of OpenAPI contract operations

**Output**: `tmp/c_graph.json`

**Example Entry**:
```json
{
  "method": "POST",
  "path": "/api/auth/login",
  "operation_id": "login",
  "request_schema": "LoginRequest",
  "response_schemas": {"200": "LoginResponse", "401": "Problem"},
  "path_params": [],
  "query_params": [],
  "source_bundle": "auth.bundled.yaml"
}
```

**Usage**:
```bash
python scripts/contracts/dump_contract_ops.py
```

**Prerequisites**: Bundled specs must exist (`api-contracts/dist/openapi/v1/*.bundled.yaml`)

---

### 4. Static Conformance Checker

**Script**: `scripts/contracts/check_static_conformance.py`

**Purpose**: Enforce bidirectional equivalence between R-Graph and C-Graph

**Checks Performed**:

1. **Implementation → Contract** (No undeclared routes)
   - Compute `R_only = R_keys - C_keys`
   - Must be empty (all implementation routes have contracts)

2. **Contract → Implementation** (No phantom operations)
   - Compute `C_only = C_keys - R_keys - allowlist`
   - Must be empty (all contract operations are implemented)

3. **Parameter Consistency**
   - For matched operations: path and query param names must match
   - Detects: `{id}` vs `{user_id}`, `cursor` vs `page`

**Usage**:
```bash
python scripts/contracts/check_static_conformance.py
```

**Exit Codes**:
- `0`: Perfect alignment (all checks pass)
- `1`: Divergence detected (with diagnostic output)

**Example Output (failure)**:
```
✗ FAIL: Found 1 undeclared implementation route(s)

These routes exist in FastAPI but have no corresponding OpenAPI contract:
  POST   /api/test/undeclared

ACTION REQUIRED: Add OpenAPI contract for these routes

Exit Code: 1
```

---

### 5. Dynamic Conformance Tests

**File**: `tests/contract/test_contract_semantics.py`

**Purpose**: Validate runtime behavior matches contract specifications

**Framework**: Schemathesis (spec-driven API testing)

**Validations**:
- Response status codes match contract-defined allowed statuses
- Response payloads validate against OpenAPI schemas
- Error responses conform to RFC7807 Problem schema
- All in-scope operations tested at least once

**Usage**:
```bash
cd tests/contract
pytest test_contract_semantics.py -v
```

**Example Test**:
```python
@schema.parametrize()
def run_test(case):
    # Execute request via ASGI (no network)
    response = case.call_asgi()
    
    # Validate against OpenAPI schema
    case.validate_response(response)
```

**Coverage Report**:
```bash
pytest test_contract_semantics.py::test_coverage_report -v -s
```

---

### 6. CI/CD Workflow

**File**: `.github/workflows/contract-enforcement.yml`

**Purpose**: Automated enforcement pipeline blocking non-conforming changes

**Job Sequence**:

```
bundle-contracts
    ↓
generate-models
    ↓
contract-static ← Blocks if structure diverges
    ↓
contract-dynamic ← Blocks if behavior diverges
    ↓
contract-enforcement-status
```

**Trigger Conditions**:
- Changes to `backend/app/api/**`
- Changes to `api-contracts/**`
- Changes to `contract_scope.yaml`

**Failure Policy**: Any job failure blocks PR merge

---

## Development Workflow

### Adding a New API Endpoint

**Correct Order** (contract-first):

1. **Define in OpenAPI Contract**
   
   Edit `api-contracts/openapi/v1/<domain>.yaml`:
   ```yaml
   /api/auth/verify-email:
     post:
       operationId: verifyEmail
       requestBody:
         required: true
         content:
           application/json:
             schema:
               $ref: '#/components/schemas/VerifyEmailRequest'
       responses:
         '200':
           content:
             application/json:
               schema:
                 $ref: '#/components/schemas/VerifyEmailResponse'
   ```

2. **Define Schemas** (if new)
   
   Add to `components/schemas` section:
   ```yaml
   VerifyEmailRequest:
     type: object
     required: [email, token]
     properties:
       email:
         type: string
         format: email
       token:
         type: string
   ```

3. **Bundle Contracts**
   ```bash
   cd api-contracts
   npx @redocly/cli bundle <domain> --output=dist/openapi/v1/<domain>.bundled.yaml --force
   ```

4. **Generate Pydantic Models**
   ```bash
   bash scripts/generate-models.sh
   ```
   
   Verify models created:
   ```bash
   python -c "from backend.app.schemas.auth import VerifyEmailRequest, VerifyEmailResponse"
   ```

5. **Implement FastAPI Route**
   
   Edit `backend/app/api/<domain>.py`:
   ```python
   from app.schemas.auth import VerifyEmailRequest, VerifyEmailResponse
   
   @router.post(
       "/verify-email",
       response_model=VerifyEmailResponse,
       status_code=200,
       operation_id="verifyEmail"
   )
   async def verify_email(request: VerifyEmailRequest):
       # Implementation
       return VerifyEmailResponse(...)
   ```

6. **Verify Conformance**
   ```bash
   python scripts/contracts/dump_routes.py
   python scripts/contracts/dump_contract_ops.py
   python scripts/contracts/check_static_conformance.py
   ```
   
   Expected: ✅ PASS

7. **Test Behavior**
   ```bash
   pytest tests/contract/test_contract_semantics.py -v
   ```
   
   Expected: ✅ PASS

8. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add verify-email endpoint (contract + implementation)"
   git push
   ```
   
   CI will validate conformance automatically.

---

### Modifying an Existing Endpoint

**Correct Order**:

1. **Update Contract First**
   - Modify `api-contracts/openapi/v1/<domain>.yaml`
   - Rebundle: `npx @redocly/cli bundle <domain> ...`

2. **Regenerate Models**
   - Run: `bash scripts/generate-models.sh`

3. **Update Implementation**
   - Modify route in `backend/app/api/<domain>.py`
   - Use updated Pydantic models

4. **Verify Conformance**
   - Static: `python scripts/contracts/check_static_conformance.py`
   - Dynamic: `pytest tests/contract/test_contract_semantics.py`

**Breaking Changes**:
- Require major version bump
- Document in `CHANGELOG.md`
- Follow migration policy

---

### Removing an Endpoint

**Correct Order**:

1. **Remove from Implementation**
   - Delete route from `backend/app/api/<domain>.py`

2. **Remove from Contract**
   - Delete operation from `api-contracts/openapi/v1/<domain>.yaml`
   - Rebundle

3. **Verify Conformance**
   - Static check should pass (no C_only or R_only)

**Alternative** (deprecation without removal):
- Mark as deprecated in contract: `deprecated: true`
- Add warning in implementation
- Plan removal for next major version

---

## CI/CD Integration

### Local Pre-Commit Validation

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Contract-First Enforcement Pre-Commit Hook

echo "Running contract conformance checks..."

# Generate graphs
python scripts/contracts/dump_routes.py || exit 1
python scripts/contracts/dump_contract_ops.py || exit 1

# Check static conformance
python scripts/contracts/check_static_conformance.py || {
    echo "❌ Static conformance check failed"
    echo "Implementation diverges from contract"
    exit 1
}

echo "✅ Contract conformance checks passed"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

### Makefile Commands

Add to `Makefile`:

```makefile
contract-check-conformance: ## Check contract-implementation conformance
	@python scripts/contracts/dump_routes.py
	@python scripts/contracts/dump_contract_ops.py
	@python scripts/contracts/check_static_conformance.py

contract-test-dynamic: ## Run dynamic contract tests
	@cd tests/contract && pytest test_contract_semantics.py -v

contract-enforce-full: ## Run full enforcement pipeline
	@echo "Running full contract enforcement pipeline..."
	@make contract-check-conformance
	@make contract-test-dynamic
	@echo "✅ Contract enforcement complete"

contract-print-scope: ## Print route classification
	@python scripts/contracts/print_scope_routes.py
```

Usage:
```bash
make contract-enforce-full
```

---

### Branch Protection Rules

**GitHub Settings → Branches → Branch protection rules**

For `main` and `develop` branches:

1. ✅ Require status checks to pass before merging
2. ✅ Require branches to be up to date before merging
3. ✅ Required status checks:
   - `bundle-contracts`
   - `generate-models`
   - `contract-static`
   - `contract-dynamic`
4. ✅ Require review from code owners (optional)
5. ✅ Include administrators (prevents bypass)

---

## Maintenance & Operations

### Monthly Allowlist Audit

**Purpose**: Ensure `contract_only_allowlist` doesn't become stale

**Procedure**:

1. Review `backend/app/config/contract_scope.yaml`
2. For each allowlisted operation:
   - Check if it's been implemented (move to R-Graph)
   - Check if still planned (keep with updated timeline)
   - Check if abandoned (remove from contract and allowlist)
3. Update allowlist and commit changes

**Automation** (recommended):

Add to CI:
```python
# scripts/contracts/audit_allowlist.py
# Fail if allowlist entries older than 90 days
```

---

### Updating Scope Configuration

**When to Update**:

| Scenario | Action |
|----------|--------|
| New API domain added | Add to `in_scope_prefixes` and `spec_mappings` |
| Internal endpoints added | Add pattern to `out_of_scope_paths` |
| Webhook domain added | Add to `in_scope_prefixes` and map to bundle |
| Admin routes created | Add `/admin/**` to `out_of_scope_paths` |

**Testing After Update**:
```bash
python scripts/contracts/print_scope_routes.py
# Verify: Zero "UNKNOWN ROUTES"
```

---

### Monitoring & Metrics

**Recommended Metrics to Track**:

1. **Enforcement Effectiveness**
   - PRs blocked by `contract-static` (per month)
   - PRs blocked by `contract-dynamic` (per month)
   - False positive rate (blocked incorrectly)

2. **Coverage**
   - Total in-scope routes
   - Contract coverage percentage
   - Test coverage per operation

3. **Developer Experience**
   - Time from divergence to detection (should be < 5 min)
   - Time from detection to fix (average)
   - Developer feedback on diagnostic quality

**Dashboard** (example):
```
Contract-First Enforcement Dashboard
─────────────────────────────────────
Total In-Scope Routes:        42
Contract Coverage:            100%
Static Check Pass Rate:       98%
Dynamic Test Pass Rate:       100%

Last 30 Days:
  PRs Blocked (Static):       3
  PRs Blocked (Dynamic):      1
  False Positives:            0
  Avg Time to Fix:            12 min
```

---

## Troubleshooting

### Issue: "R-Graph not found" Error

**Symptom**:
```
ERROR: R-Graph not found at tmp/r_graph.json
Please run: python scripts/contracts/dump_routes.py
```

**Cause**: `dump_routes.py` hasn't been run yet

**Solution**:
```bash
python scripts/contracts/dump_routes.py
```

---

### Issue: "Cannot import FastAPI app" Error

**Symptom**:
```
ERROR: Cannot import FastAPI app: No module named 'app'
```

**Cause**: Python path not set correctly

**Solution**:
```bash
# Ensure you're running from repo root
cd <repo-root>
export PYTHONPATH="${PWD}/backend:${PYTHONPATH}"
python scripts/contracts/dump_routes.py
```

---

### Issue: "Undeclared routes" but Route Has Contract

**Symptom**: Static check fails with `R_only` error, but you know the contract exists

**Possible Causes**:
1. **Bundled spec outdated**: Run bundling again
2. **Path mismatch**: `/api/auth/login` vs `/api/auth/login/`
3. **Spec not in C-Graph**: Operation filtered by scope config

**Debug Steps**:
```bash
# 1. Rebundle
cd api-contracts
npx @redocly/cli bundle <domain> --output=dist/openapi/v1/<domain>.bundled.yaml --force

# 2. Regenerate C-Graph
python scripts/contracts/dump_contract_ops.py

# 3. Inspect C-Graph
cat tmp/c_graph.json | grep "login"

# 4. Inspect R-Graph
cat tmp/r_graph.json | grep "login"

# 5. Compare paths exactly (case-sensitive, trailing slashes)
```

---

### Issue: Schemathesis Validation Failure

**Symptom**:
```
Schemathesis schema validation error:
  Response body does not match schema
```

**Debug Steps**:

1. **Check actual vs expected response**:
   ```python
   # Add to test for debugging
   print("Actual response:", response.json())
   ```

2. **Inspect schema in bundle**:
   ```bash
   # Find response schema in bundled spec
   grep -A 20 "LoginResponse" api-contracts/dist/openapi/v1/auth.bundled.yaml
   ```

3. **Verify Pydantic model matches contract**:
   ```python
   from backend.app.schemas.auth import LoginResponse
   print(LoginResponse.model_json_schema())
   ```

4. **Common Fixes**:
   - Missing required field: Add to implementation
   - Wrong field type: Fix type in implementation or contract
   - Extra field: Remove from implementation or add to contract

---

### Issue: CI Passes Locally But Fails in GitHub Actions

**Possible Causes**:

1. **Stale artifacts**: GitHub Actions caches bundled specs
   - Solution: Clear cache or bump workflow version

2. **Environment differences**: Python/Node version mismatch
   - Solution: Match versions in workflow to local

3. **File path issues**: Windows vs Linux path separators
   - Solution: Use `Path` from `pathlib` (already implemented)

4. **Missing dependencies**:
   - Solution: Ensure `backend/requirements-dev.txt` complete

---

## References

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/config/contract_scope.yaml` | Scope configuration |
| `scripts/contracts/dump_routes.py` | R-Graph generation |
| `scripts/contracts/dump_contract_ops.py` | C-Graph generation |
| `scripts/contracts/check_static_conformance.py` | Static conformance checker |
| `tests/contract/test_contract_semantics.py` | Dynamic conformance tests |
| `.github/workflows/contract-enforcement.yml` | CI workflow |

### Related Documentation

- [Forensic Validation Report](./contract-enforcement-validation-report.md): Empirical evidence of enforcement
- [Negative Test Scenarios - Static](../../tests/contract/negative_tests_static.md): Static conformance test cases
- [Negative Test Scenarios - Dynamic](../../tests/contract/negative_tests_dynamic.md): Dynamic conformance test cases
- [Pydantic Pipeline Remediation](./pydantic-pipeline-remediation.md): Model generation docs
- [API Contracts README](../../api-contracts/README.md): Contract documentation

### External Resources

- [Schemathesis Documentation](https://schemathesis.readthedocs.io/)
- [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0)
- [RFC 7807: Problem Details](https://datatracker.ietf.org/doc/html/rfc7807)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Support & Contact

For questions or issues with contract-first enforcement:

1. Check this documentation and troubleshooting section
2. Review forensic validation report for examples
3. Consult negative test scenarios for failure modes
4. Open issue with diagnostic output from failed checks

---

**Document Version**: 1.0  
**Last Updated**: Implementation Complete  
**Status**: ✅ Operational





