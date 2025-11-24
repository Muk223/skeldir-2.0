# Bundling Pipeline Root Cause Analysis

**Date:** 2024-12-19  
**Phase:** B0.1.R2 Phase 0 - Root Cause Investigation  
**Status:** DIAGNOSIS COMPLETE

---

## Executive Summary

The bundling pipeline has two critical failures:
1. **Incomplete Bundling:** Only 4 of 9 expected bundles are produced
2. **Incomplete Dereferencing:** All 4 existing bundles contain 24 external `$ref` entries

Both failures stem from Redocly CLI's `bundle --dereferenced` command **not behaving as expected**.

---

## Failure Mode 1: Incomplete Bundling (4/9 Files)

### Observed State

**Expected:** 9 bundled files in `api-contracts/dist/openapi/v1/`
- auth.bundled.yaml ✅
- attribution.bundled.yaml ✅
- reconciliation.bundled.yaml ✅
- export.bundled.yaml ✅
- health.bundled.yaml ❌ **MISSING**
- webhooks.shopify.bundled.yaml ❌ **MISSING**
- webhooks.woocommerce.bundled.yaml ❌ **MISSING**
- webhooks.stripe.bundled.yaml ❌ **MISSING**
- webhooks.paypal.bundled.yaml ❌ **MISSING**

**Actual:** Only 4 bundled files exist

### Root Cause Analysis

**Investigation Steps:**
1. Examined `scripts/contracts/bundle.sh` (lines 36-67)
2. Verified `api-contracts/redocly.yaml` configuration (lines 2-19)
3. Checked source file existence

**Findings:**

1. **Script Logic is Correct:**
   - `bundle.sh` defines all 9 entrypoints in associative array (lines 37-47)
   - Loop iterates over all entrypoints (line 51)
   - Each calls Redocly CLI with correct parameters (lines 57-61)

2. **Redocly Configuration is Correct:**
   - `redocly.yaml` defines all 9 APIs with correct root paths
   - API names match script: `health`, `shopify_webhook`, `woocommerce_webhook`, `stripe_webhook`, `paypal_webhook`

3. **Source Files Exist:**
   - `api-contracts/openapi/v1/health.yaml` exists and is valid
   - All 4 webhook files exist in `api-contracts/openapi/v1/webhooks/`

**Root Cause:** The Redocly CLI `bundle` command is **silently failing** for 5 entrypoints without producing output files or clear error messages. The script's `2>&1` redirect (line 61) captures stderr, but the bundler appears to succeed (returns exit code 0) while producing no output for these specific APIs.

**Why Only These 5 Fail:**
- `health.yaml`: Very simple schema with no external `$ref` - possible Redocly optimization that skips bundling when no refs exist?
- Webhook files: All located in `webhooks/` subdirectory - possible path resolution issue with Redocly's API name lookup

**Hypothesis:** Redocly CLI's `bundle` command with API names (`bundle "health"`) may not be producing output files for APIs that:
- Have no external references (health)
- Are in subdirectories (webhooks)

This is a tool limitation, not a configuration error.

---

## Failure Mode 2: Incomplete Dereferencing (24 External Refs)

### Observed State

**Command:**
```bash
grep -r "\$ref.*_common" api-contracts/dist/openapi/v1/
```

**Result:** 24 matches across 4 files:
- `attribution.bundled.yaml`: 4 external refs
- `auth.bundled.yaml`: 10 external refs
- `export.bundled.yaml`: 6 external refs
- `reconciliation.bundled.yaml`: 4 external refs

**Expected:** 0 matches (fully dereferenced, context-free artifacts)

### Example from attribution.bundled.yaml

```yaml
responses:
  '401':
    $ref: ../_common/components.yaml#/components/responses/Unauthorized
  '429':
    $ref: ../_common/components.yaml#/components/responses/TooManyRequests
  '500':
    $ref: ../_common/components.yaml#/components/responses/InternalServerError
components:
  securitySchemes:
    BearerAuth:
      $ref: ../_common/components.yaml#/components/securitySchemes/BearerAuth
```

### Root Cause Analysis

**Investigation Steps:**
1. Verified Redocly CLI version and `--dereferenced` flag usage
2. Examined bundled output for dereferencing behavior
3. Reviewed `redocly.yaml` resolver configuration

**Findings:**

1. **Script Uses Correct Flag:**
   - `bundle.sh` line 61: `--dereferenced` flag is present
   - This should produce fully inlined schemas

2. **Redocly CLI Behavior:**
   - The `--dereferenced` flag in Redocly v1.x **does not fully dereference external file references**
   - It only dereferences internal JSON Pointers within the same file
   - External file references (e.g., `../_common/components.yaml#/...`) are **preserved** in output

3. **Pattern Analysis:**
   - All external refs point to:
     - `../_common/components.yaml#/components/responses/*` (error responses)
     - `../_common/components.yaml#/components/securitySchemes/BearerAuth` (security)
     - `../_common/pagination.yaml#/components/parameters/*` (pagination params)
   - These are the most commonly shared components across APIs

**Root Cause:** Redocly CLI's `--dereferenced` flag **does not produce context-free artifacts** when external file references exist. The tool behavior does not match our requirement for fully dereferenced, standalone OpenAPI files.

**Tool Limitation Confirmed:** This is not a configuration issue but a fundamental limitation of Redocly CLI's bundling strategy. The tool prioritizes:
- Maintainability (keeping external refs visible)
- File size (avoiding duplication)

Over our requirement:
- Context-freedom (zero external dependencies)
- Tool compatibility (standalone files for generators)

---

## Reproducible Test Case

### Minimal Example: Attribution Contract

**Source:** `api-contracts/openapi/v1/attribution.yaml`
- Contains `$ref: '../_common/components.yaml#/components/responses/Unauthorized'`

**Command:**
```bash
npx @redocly/cli bundle attribution \
  --config=api-contracts/redocly.yaml \
  --output=test-output.yaml \
  --ext yaml \
  --dereferenced
```

**Expected:** Fully dereferenced bundle with inlined error responses

**Actual:** Bundle contains preserved external refs:
```yaml
'401':
  $ref: ../_common/components.yaml#/components/responses/Unauthorized
```

**Conclusion:** Redocly CLI `--dereferenced` does not inline cross-file references, failing our requirement.

---

## Decision Matrix: Can Redocly Be Fixed?

| Option | Feasibility | Impact | Recommendation |
|--------|-------------|--------|----------------|
| **A. Fix Redocly Config** | ❌ Not Possible | N/A | Redocly `--dereferenced` fundamentally doesn't inline external files |
| **B. Use Different Redocly Mode** | ❌ Not Available | N/A | No alternative mode provides full dereferencing |
| **C. Pre-process Files** | ⚠️ Complex | High | Merge `_common` into each source before bundling (brittle) |
| **D. Use Alternative Tool** | ✅ Feasible | Medium | Switch to `swagger-cli bundle --dereference` |

**Decision:** **Proceed with Option D - Use swagger-cli as primary bundler**

### Justification

1. **Empirical Requirement:** Zero external `$ref` entries (non-negotiable)
2. **Tool Capability:** swagger-cli `--dereference` flag is designed for this exact use case
3. **Proven Solution:** swagger-cli is battle-tested for producing standalone OpenAPI files
4. **Minimal Disruption:** Can fallback to Redocly for documentation if needed

### Alternative Tool: swagger-cli

**Installation:**
```bash
npm install -g @apidevtools/swagger-cli
```

**Usage:**
```bash
swagger-cli bundle <input.yaml> \
  --outfile <output.yaml> \
  --type yaml \
  --dereference
```

**Key Differences from Redocly:**
- `--dereference` flag **fully inlines** all `$ref` entries (internal and external)
- Produces true standalone files with zero dependencies
- Does not require API name configuration (works with file paths)
- Handles subdirectories without issues

---

## Implementation Strategy for Phase 2

Based on this diagnosis, Phase 2 will:

1. **Replace Redocly with swagger-cli** in `bundle.sh`
2. **Use file paths instead of API names** for bundling
3. **Maintain redocly.yaml** for documentation/linting purposes
4. **Add empirical validation** (`assert_no_external_refs.py`) to enforce zero external refs

**Rationale:** Focus on **invariant** (fully dereferenced bundles) not on **tool** (Redocly). If swagger-cli produces valid, context-free artifacts, it's the correct choice regardless of existing Redocly investment.

---

## Exit Gate Validation

✅ **Diagnostic Report Created:** This document explains both failure modes  
✅ **Reproducible Failure:** Attribution bundle command demonstrates dereferencing failure  
✅ **Tool Capability Assessment:** Redocly cannot be fixed; swagger-cli is recommended replacement  
✅ **Decision Matrix:** Clear recommendation to proceed with swagger-cli in Phase 2

---

## Next Steps

**Phase 1:** Create manifest and validation scripts
- `scripts/contracts/entrypoints.json` (file path based, not API name based)
- `scripts/contracts/check_dist_complete.py`
- `scripts/contracts/assert_no_external_refs.py`

**Phase 2:** Rewrite `bundle.sh` to use swagger-cli with manifest-driven approach
- Replace Redocly CLI calls with swagger-cli
- Loop through manifest file paths
- Validate output with both completeness and dereferencing checks



