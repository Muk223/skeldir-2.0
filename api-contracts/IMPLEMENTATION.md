# B0.1.R Contract Bundling Remediation - Implementation Document

## Context and Rationale

The Skeldir platform employs a **Contract-First** architecture where OpenAPI specifications act as executable source code driving downstream artifacts (Pydantic models, mock servers, frontend SDKs).

**Problem Statement:**
Previous attempts to validate split YAML files failed due to tool inability to resolve relative references to the `_common` directory, resulting in a broken build pipeline and empty model files.

**The Remediation Architecture:**
We are introducing a **Bundling Strategy**.
- **Source:** Split YAML files (Human readable, maintainable) in `api-contracts/openapi/v1/`
- **Process:** `Redocly` bundles references into a single context
- **Target:** Monolithic YAML artifacts (Machine readable, tool compliant) in `api-contracts/dist/openapi/v1/`

**Critical Technical Decision:**
We explicitly reject modifying the folder structure to flatten the files. We will maintain the domain-driven directory structure (`auth.yaml`, `attribution.yaml`) and solve the resolution issue via the ephemeral `dist/` bundling step. This preserves the "DRY" architectural desire while satisfying the "Tool-Valid" requirement.

---

## Toolchain Versions & Commands

### Node.js
- **Version:** 20.x (LTS)
- **Configuration:** `.nvmrc` file specifies `20`
- **Verification:** `node -v` should return `v20.x.x`

### Redocly CLI
- **Version:** 1.15.0
- **Package:** `@redocly/cli`
- **Installation:** `npm install` (included in `package.json` devDependencies)
- **Canonical Command:**
  ```bash
  npx @redocly/cli bundle <entrypoint> \
    --config=api-contracts/redocly.yaml \
    --output=api-contracts/dist/openapi/v1/<name>.bundled.yaml \
    --ext yaml \
    --dereferenced
  ```
- **Verification:** `npx @redocly/cli --version` should return `1.15.0`

### OpenAPI Generator CLI
- **Version:** 7.17.0
- **Package:** `@openapitools/openapi-generator-cli`
- **Configuration:** `openapitools.json` specifies version
- **Canonical Command:**
  ```bash
  npx @openapitools/openapi-generator-cli validate -i api-contracts/dist/openapi/v1/<name>.bundled.yaml
  ```
- **Verification:** `npx @openapitools/openapi-generator-cli version` should return `7.17.0`

### datamodel-code-generator
- **Version:** 0.25.0
- **Package:** `datamodel-code-generator`
- **Installation:** `pip install -r backend/requirements-dev.txt`
- **Canonical Command:**
  ```bash
  python -m datamodel_code_generator \
    --input api-contracts/dist/openapi/v1/<name>.bundled.yaml \
    --input-file-type openapi \
    --output /tmp/contract-models
  ```
- **Verification:** `python -m datamodel_code_generator --version` should return `0.25.0`

### Python
- **Version:** 3.11
- **Verification:** `python --version` should return `Python 3.11.x`

---

## Execution Dependency Graph

- **Phase 0 (Toolchain Baseline)** validates that the environment is reproducible
- **Phase 1 (Dependency Graph)** makes the source file structure explicit
- **Phase 2 (Bundling Pipeline)** validates that source files are readable and can be bundled
- **Phase 3 (Source Normalization)** ensures source files contain valid component definitions
- **Phase 2 + Phase 3** are prerequisites for **Phase 4 (Local Workflow)**
- **Phase 4** is prerequisite for **Phase 5 (CI Integration)**
- **Phase 5** is prerequisite for resuming **Phase B0.2 (Mock Server)** and **B0.4 (Ingestion)**

---

## System Invariants

1. **All downstream tools use bundled artifacts only.**
   - `openapi-generator-cli validate` runs on `api-contracts/dist/*.bundled.yaml`
   - `datamodel-codegen` runs on `api-contracts/dist/*.bundled.yaml`
   - Any future docs/mocks/SDK generators must use `api-contracts/dist/` as input

2. **Source vs. dist roles are explicit.**
   - `api-contracts/openapi/v1/` = hand-edited source specs
   - `api-contracts/dist/openapi/v1/` = machine-generated bundles (never hand-edited)

3. **Operational ≠ Functional.**
   - "Operational" here **does not** mean:
     * "The YAML parses"
     * "The bundler runs"
   - It means:
     * Bundles exist **for all entrypoints**
     * Bundles are **valid** OpenAPI for `openapi-generator-cli`
     * Bundles are **consumable** by `datamodel-codegen` and yield meaningful models (non-empty where expected)

---

## Phase 1: Contract Inventory & `_common` Dependency Graph

See `DEPENDENCY_GRAPH.md` for complete dependency mapping.

**Summary:**
- **Entrypoints:** 9 total (5 domain: auth, attribution, reconciliation, export, health; 4 webhook: shopify, woocommerce, stripe, paypal)
- **Common Files:** 2 (`components.yaml`, `pagination.yaml`)
- **$ref Pattern:** Consistent `../_common/<file>.yaml#/components/...` across all specs
- **Known Issues:** 
  - Inline `RealtimeRevenueResponse` schema in `attribution.yaml` (needs extraction in Phase 3)
  - `health.yaml` has no external dependencies (will bundle cleanly)

**Dependency Graph:** Complete mapping of all `$ref` entries with source file, target file, component type, and usage counts documented in `DEPENDENCY_GRAPH.md`.

---

## Phase 2: Redocly Bundling Pipeline

**Implementation:**
- **Redocly Config:** `api-contracts/redocly.yaml` defines all 9 entrypoints (5 domain + 4 webhook)
- **Bundling Script:** `scripts/contracts/bundle.sh` bundles all entrypoints into `api-contracts/dist/openapi/v1/*.bundled.yaml`
- **Bundling Command:** `npx @redocly/cli bundle <entrypoint> --config=api-contracts/redocly.yaml --output=<dist>/<name>.bundled.yaml --ext yaml --dereferenced`
- **Verification:** Script verifies zero external `$ref` entries remain after bundling

**Entrypoints Bundled:**
1. `auth` → `auth.bundled.yaml`
2. `attribution` → `attribution.bundled.yaml`
3. `reconciliation` → `reconciliation.bundled.yaml`
4. `export` → `export.bundled.yaml`
5. `health` → `health.bundled.yaml`
6. `shopify_webhook` → `webhooks.shopify.bundled.yaml`
7. `woocommerce_webhook` → `webhooks.woocommerce.bundled.yaml`
8. `stripe_webhook` → `webhooks.stripe.bundled.yaml`
9. `paypal_webhook` → `webhooks.paypal.bundled.yaml`

**Dist Directory:** `api-contracts/dist/openapi/v1/` (added to `.gitignore`)

---

## Phase 3: Source Spec Normalization for Robust Bundling

**Implementation:**
- **Inline Schema Extraction:** Extracted `RealtimeRevenueResponse` from inline definition in `attribution.yaml` to `components/schemas/RealtimeRevenueResponse`
- **$ref Normalization:** Verified all cross-file refs use consistent `../_common/...` pattern (no mixed styles found)
- **Path Corrections:**
  - Updated `scripts/generate-models.sh` to use `api-contracts/dist/openapi/v1/*.bundled.yaml` instead of `contracts/` paths
  - Updated `.github/workflows/contract-validation.yml` to use `api-contracts/` paths throughout
  - Model generation now requires bundled artifacts (enforces bundling-first workflow)

**Schema Extraction:**
- `attribution.yaml`: `RealtimeRevenueResponse` now exists as named component, enabling meaningful Pydantic model generation

---

## Phase 4: Local Validation Harness & Developer Workflow

**Implementation:**
- **Unified Command:** `make contracts-check` or `./scripts/contracts/check.sh`
- **Workflow Steps:**
  1. Bundle all entrypoints (`bundle.sh`)
  2. Validate all bundled files (`openapi-generator-cli validate`)
  3. Optional: Model generation smoke test (`datamodel-codegen` on auth + attribution)
- **Focused Commands:**
  - `make contracts-check-auth` - Validate auth contract only
  - `make contracts-check-attribution` - Validate attribution contract only
  - `make contracts-check-smoke` - Include model generation smoke test

**Pre-commit Hook:**
- Sample hook provided at `.git/hooks/pre-commit.sample.contracts` (non-mandatory, warnings only)
- Developers can opt-in by copying to `.git/hooks/pre-commit`

**Developer Workflow:**
- Run `make contracts-check` before committing contract changes
- Run `make contracts-check-smoke` to verify model generation works
- CI will enforce full validation, but local checks catch issues early

---

## Phase 5: CI Validation Gate & datamodel-codegen Integration

**Implementation:**
- **CI Workflow Updates:** `.github/workflows/contract-validation.yml`
  - Fixed paths: All references updated from `contracts/` to `api-contracts/`
  - Added `bundle-contracts` job that runs before validation
  - Updated trigger paths to include `api-contracts/**/*.yaml` and `scripts/contracts/**`
- **Bundling Step:** All validation jobs now depend on `bundle-contracts` job
- **Model Generation:** 
  - Requires bundled artifacts (enforces bundling-first)
  - Smoke test verifies `RealtimeRevenueResponse` class generation for attribution
  - Uses pinned `datamodel-codegen` version from `backend/requirements-dev.txt`
- **Job Dependencies:**
  - `bundle-contracts` → `validate-openapi` → `generate-models`
  - All jobs are blocking (no "allow failure")

**CI Jobs:**
1. `bundle-contracts` - Bundles all entrypoints, verifies 9 artifacts created
2. `validate-openapi` - Validates all bundled files with `openapi-generator-cli`
3. `check-breaking-changes` - Compares against baselines using `oasdiff`
4. `enforce-semver` - Validates semantic versioning format
5. `generate-models` - Generates Pydantic models from bundled artifacts, runs smoke tests

---

## Phase 6: Aggregate System Alignment & Final Exit Gates

### Global Minimum Requirements

1. **Bundling is Standard Path**
   - ✅ Every contract-dependent tool uses `api-contracts/dist/openapi/v1/*.bundled.yaml` as inputs
   - ✅ No tooling touches multi-file source tree directly
   - ✅ `scripts/generate-models.sh` requires bundled artifacts

2. **Source Specs are Stable Inputs**
   - ✅ Multi-file source tree is structured consistently
   - ✅ All `$ref` paths use consistent `../_common/...` pattern
   - ✅ Inline schemas extracted to named components (e.g., `RealtimeRevenueResponse`)

3. **Toolchain is Deterministic**
   - ✅ Pinned versions: Node 20.x, Redocly CLI 1.15.0, openapi-generator-cli 7.17.0, datamodel-codegen 0.25.0
   - ✅ All versions documented in this Implementation Document
   - ✅ `.nvmrc` and `package.json` enforce Node version

4. **Operational Definition is Concrete**
   - ✅ Contract change is "operationally acceptable" ONLY if:
     - `bundle.sh` succeeds on all entrypoints
     - `openapi-generator-cli validate` passes for all bundles
     - `datamodel-codegen` generates meaningful models (non-empty where expected)

### System-Level Exit Gates

1. **Fresh-Environment Test**
   - Brand-new environment following this document can:
     - Install toolchain (Node 20.x, npm install, pip install -r backend/requirements-dev.txt)
     - Run `make contracts-check` (or `./scripts/contracts/check.sh`)
     - Observe: all bundles generated, all bundles validated, generator smoke checks passing

2. **No Hidden Manual Procedures**
   - ✅ No undocumented local hacks required
   - ✅ Everything encoded in scripts + config:
     - `scripts/contracts/bundle.sh` - Bundling logic
     - `scripts/contracts/check.sh` - Validation pipeline
     - `scripts/generate-models.sh` - Model generation
     - `api-contracts/redocly.yaml` - Bundler configuration
     - `.github/workflows/contract-validation.yml` - CI enforcement

3. **Integrated Implementation Document**
   - ✅ This document contains:
     - Context and rationale for bundling
     - Toolchain baseline (Phase 0)
     - `_common` dependency graph summary (Phase 1)
     - Bundling architecture and scripts (Phase 2)
     - Source normalization rules (Phase 3)
     - Local developer workflow (Phase 4)
     - CI pipeline and enforcement semantics (Phase 5)
     - Global system requirements and final exit gates (Phase 6)

4. **Traceable Failure & Ownership**
   - ✅ If `contracts` CI job fails:
     - `bundle-contracts` job shows which entrypoint failed bundling
     - `validate-openapi` job shows which bundled file failed validation
     - `generate-models` job shows which bundle failed model generation
     - Source spec and `$ref` responsible can be traced via `DEPENDENCY_GRAPH.md`
   - ✅ Clear remediation process:
     1. Check CI job logs for specific failure
     2. Run `make contracts-check` locally to reproduce
     3. Fix source spec or `_common` component
     4. Re-run validation until clean

### Troubleshooting Guide

**Bundling Failures:**
- Check `api-contracts/redocly.yaml` has correct entrypoint definitions
- Verify `$ref` paths in source specs match actual file structure
- Run `npx @redocly/cli bundle <entrypoint> --config=api-contracts/redocly.yaml --output=/tmp/test.yaml --dereferenced` to test individual entrypoint

**Validation Failures:**
- Ensure bundled files exist in `api-contracts/dist/openapi/v1/`
- Check for external `$ref` entries: `grep -r "\$ref.*_common" api-contracts/dist/` (should return nothing)
- Verify OpenAPI 3.1.0 structure is valid

**Model Generation Failures:**
- Ensure bundled artifacts exist (run `make contracts-check` first)
- Check that schemas are named components (not inline)
- Verify `datamodel-codegen` version matches `backend/requirements-dev.txt`

**CI Failures:**
- Check job dependencies: `bundle-contracts` must succeed before `validate-openapi` and `generate-models`
- Verify paths are correct: all references should use `api-contracts/` not `contracts/`
- Check Node.js version matches `.nvmrc` (20.x)

---

## Summary

The B0.1.R Contract Bundling Remediation has been successfully implemented across all 6 phases:

- ✅ **Phase 0:** Toolchain versions pinned and documented
- ✅ **Phase 1:** Complete dependency graph mapped
- ✅ **Phase 2:** Redocly bundling pipeline operational
- ✅ **Phase 3:** Source specs normalized, inline schemas extracted, paths corrected
- ✅ **Phase 4:** Local validation harness and developer workflow established
- ✅ **Phase 5:** CI integration with bundling-first enforcement
- ✅ **Phase 6:** System alignment complete, Implementation Document finalized

**Result:** All OpenAPI contracts are now tool-valid and executable. The bundling pipeline produces context-free, deterministic artifacts that are consumable by `openapi-generator-cli` and `datamodel-codegen`, enabling meaningful Pydantic model generation and downstream tooling.

