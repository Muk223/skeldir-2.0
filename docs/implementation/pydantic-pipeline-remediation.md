# OpenAPI → Pydantic Model Generation & Enforcement

## Context & Failure Analysis

**Problem Statement:** The current OpenAPI→Pydantic generation pipeline is **decorative, not operational**. Running `scripts/generate-models.sh` produces placeholder files containing only stub comments (`# No models generated - attribution.yaml uses inline schemas`). This occurs because:

1. Bundled contracts are not present (`api-contracts/dist/openapi/v1/` is empty)
2. Source contracts contain inline schemas that `datamodel-codegen` cannot assign Python class names to
3. No CI enforcement validates that generated models are live dependencies

**Architectural Imperative:** In Skeldir's compliance-focused, Bayesian-statistical backend, Pydantic models are the **typed embodiment of the contract**. If generation is decorative, then:

- The "backend uses contract-derived types" invariant is false
- Divergence between contract and implementation can silently accumulate
- Downstream automation (SDKs, type checking, statistical layers) becomes fragile

## Remediation Phases

### Phase P0: Bundling Preconditions & Tooling Baseline

**Intent:** Establish deterministic contract bundling that produces fully dereferenced, single-file OpenAPI artifacts.

**Key Steps:**
- Verify Node.js ≥20 and npm are installed
- Execute `bash scripts/contracts/bundle.sh` to bundle all 9 entrypoints
- Verify bundled files exist and contain actual schema content (not just file paths)
- Document `datamodel-codegen` configuration flags

**Exit Gates:**
- All 9 bundled files exist in `api-contracts/dist/openapi/v1/`
- Bundled files contain actual schema content (e.g., `total_revenue` field)
- Generator flags are documented

### Phase P1: Contract Schema Surface Design for Generation

**Intent:** Refactor all contracts so `datamodel-codegen` is **forced** to produce meaningful Pydantic models by moving inline schemas to `components/schemas`.

**Key Steps:**
- Identify all inline schemas in requestBody/responses sections
- Extract schemas to `components/schemas` with PascalCase names
- Replace inline schemas with `$ref` references
- Rebundle contracts after refactoring

**DTOs Componentized:**
- `auth.yaml`: LoginRequest, LoginResponse, RefreshRequest, RefreshResponse, LogoutResponse
- `reconciliation.yaml`: ReconciliationStatusResponse
- `export.yaml`: ExportRevenueResponse
- `webhooks/shopify.yaml`: ShopifyOrderCreateRequest, WebhookAcknowledgement
- `webhooks/woocommerce.yaml`: WooCommerceOrderCreateRequest, WebhookAcknowledgement
- `webhooks/stripe.yaml`: StripeChargeSucceededRequest, WebhookAcknowledgement
- `webhooks/paypal.yaml`: PayPalSaleCompletedRequest, WebhookAcknowledgement

**Exit Gates:**
- All critical DTOs exist as named schemas in `components/schemas`
- Generator produces model classes for all canonical DTOs
- No inline schemas remain in operation definitions

### Phase P2: Bundled-Contract → Pydantic Generation Pipeline

**Intent:** Implement a **repeatable, automated** pipeline that generates Pydantic models and **fails loudly** if generation is empty or broken.

**Key Steps:**
- Remove placeholder logic from `scripts/generate-models.sh`
- Add post-generation validation (file exists, contains classes, >100 bytes)
- Add import sanity check at end of script
- Update `__init__.py` to remove try/except suppression

**Exit Gates:**
- Script exits with code 0 only if all models are generated and importable
- Script fails on any generation or import failure
- Generated files contain actual Pydantic classes

### Phase P3: Backend Integration Validation (CI-Only)

**Intent:** Establish CI mechanisms to validate that generated Pydantic models are **structurally prepared** for use at the FastAPI boundary.

**Key Steps:**
- Create `scripts/validate_model_usage.py` to validate model structures
- Create `backend/tests/test_generated_models.py` with instantiation tests
- Document model usage rules for future route implementation

**Exit Gates:**
- Validation script checks model structures match contract specs
- Unit tests instantiate models with valid/invalid data
- Tests fail when models are broken (runtime validation)

### Phase P4: CI Enforcement & Semantic Validation

**Intent:** Turn generation + validation rules into **hard, automated constraints** in CI.

**Key Steps:**
- Enhance `generate-models` CI job with non-trivial validation
- Add `validate-model-structures` CI job
- Both jobs run on contract and backend schema changes

**Exit Gates:**
- CI fails if models are missing, empty, or structurally incorrect
- CI validates critical model classes exist
- CI runs model structure validation and unit tests

### Phase P5: System Alignment

**Intent:** Integrate all prior phases into a coherent system with complete documentation.

**Key Steps:**
- Create unified Implementation Document (this file)
- Create Quick Reference Guide
- Create Integration Test Script
- Update CONTRIBUTING.md with contract-first workflow

**Exit Gates:**
- All documentation artifacts exist
- Integration test script passes
- Fresh environment can follow documentation to complete pipeline

## Operational Procedures

### Adding a New DTO to Contracts

1. Define schema in contract's `components/schemas` section (PascalCase name)
2. Reference via `$ref: '#/components/schemas/YourDto'` in operation
3. Run `bash scripts/contracts/bundle.sh`
4. Run `bash scripts/generate-models.sh`
5. Verify generated class exists: `grep "class YourDto" backend/app/schemas/domain.py`
6. Add model to validation script's expected models list
7. Commit contract + updated schemas + validation updates together

### Consuming Generated Models in Backend Routes

When implementing FastAPI routes:
- Import generated models: `from backend.app.schemas.auth import LoginRequest, LoginResponse`
- Use as type hints: `def login(request: LoginRequest) -> LoginResponse:`
- Do NOT define ad-hoc Pydantic models for contract-shaped payloads

### Handling Contract Schema Changes

#### Non-Breaking (Minor Version)
- Adding optional fields: Safe, no model regeneration issues
- Procedure: Update contract → rebundle → regenerate models → verify tests pass

#### Breaking (Major Version)
- Removing required fields, changing field types: Breaking
- Procedure: Update baselines → bump version → migration guide → regenerate models
- CI will catch breaking changes via `oasdiff breaking` check

## Maintenance Invariants

Going forward, the following must remain true:

1. All API request/response payloads are defined as named schemas in `components/schemas`
2. Generated models are **never** hand-edited (always regenerated from contracts)
3. CI blocks any PR where contracts change but models don't regenerate correctly
4. Adding a new endpoint requires: contract schema → bundle → generate → validate → commit all together



