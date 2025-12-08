# Contract Dependency Graph

This document maps all `$ref` dependencies across the OpenAPI contract files to enable accurate bundler configuration and deterministic failure diagnosis.

## Entrypoint Files

### Domain Contracts
1. `auth.yaml` - Authentication and authorization endpoints
2. `attribution.yaml` - Attribution and revenue verification endpoints
3. `reconciliation.yaml` - Reconciliation and verification pipeline status endpoints
4. `export.yaml` - Data export endpoints
5. `health.yaml` - Health check endpoints (no external dependencies)

### Webhook Contracts
1. `webhooks/shopify.yaml` - Shopify webhook ingestion
2. `webhooks/woocommerce.yaml` - WooCommerce webhook ingestion
3. `webhooks/stripe.yaml` - Stripe webhook ingestion
4. `webhooks/paypal.yaml` - PayPal webhook ingestion

## Common Component Files

1. `_common/components.yaml` - Security schemes, headers, error schemas, and response templates
2. `_common/pagination.yaml` - Pagination parameters and envelope schemas
3. `_common/parameters.yaml` - Shared parameter definitions (currently not referenced by entrypoints)

## Dependency Table

| Source Spec | Target File | Component Type | Component Path | Usage Count |
|------------|-------------|----------------|----------------|-------------|
| `auth.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 3 |
| `auth.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/TooManyRequests` | 3 |
| `auth.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/InternalServerError` | 3 |
| `auth.yaml` | `_common/components.yaml` | `securitySchemes` | `#/components/securitySchemes/BearerAuth` | 1 |
| `attribution.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `attribution.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/TooManyRequests` | 1 |
| `attribution.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/InternalServerError` | 1 |
| `attribution.yaml` | `_common/components.yaml` | `securitySchemes` | `#/components/securitySchemes/BearerAuth` | 1 |
| `reconciliation.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `reconciliation.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/TooManyRequests` | 1 |
| `reconciliation.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/InternalServerError` | 1 |
| `reconciliation.yaml` | `_common/components.yaml` | `securitySchemes` | `#/components/securitySchemes/BearerAuth` | 1 |
| `export.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `export.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/TooManyRequests` | 1 |
| `export.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/InternalServerError` | 1 |
| `export.yaml` | `_common/components.yaml` | `securitySchemes` | `#/components/securitySchemes/BearerAuth` | 1 |
| `export.yaml` | `_common/pagination.yaml` | `parameters` | `#/components/parameters/limit` | 1 |
| `export.yaml` | `_common/pagination.yaml` | `parameters` | `#/components/parameters/cursor` | 1 |
| `webhooks/shopify.yaml` | `_common/components.yaml` | `schemas` | `#/components/schemas/Problem` | 1 |
| `webhooks/shopify.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `webhooks/woocommerce.yaml` | `_common/components.yaml` | `schemas` | `#/components/schemas/Problem` | 1 |
| `webhooks/woocommerce.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `webhooks/stripe.yaml` | `_common/components.yaml` | `schemas` | `#/components/schemas/Problem` | 1 |
| `webhooks/stripe.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |
| `webhooks/paypal.yaml` | `_common/components.yaml` | `schemas` | `#/components/schemas/Problem` | 1 |
| `webhooks/paypal.yaml` | `_common/components.yaml` | `responses` | `#/components/responses/Unauthorized` | 1 |

## $ref Pattern Analysis

### Pattern Consistency
All cross-file references use the consistent pattern: `../_common/<file>.yaml#/components/<type>/<name>`

- **No mixed path styles** (e.g., no `./_common` vs `../_common` inconsistencies)
- **All relative paths** are relative to the file location
- **All references** use the `#/components/` JSON pointer syntax

### Local References (within same file)
- `_common/components.yaml` uses local references: `#/components/headers/...`, `#/components/schemas/Problem`
- These are internal to the file and will be inlined during bundling

## Known Issues & Flags

### Inline Schemas Requiring Extraction
1. **`attribution.yaml`** (lines 40-64):
   - Inline `RealtimeRevenueResponse` schema in `/api/attribution/revenue/realtime` GET response
   - **Action Required:** Extract to `components/schemas/RealtimeRevenueResponse` in `attribution.yaml`
   - **Reason:** Enables meaningful Pydantic model generation (datamodel-codegen requires named schemas)

### Unused Common Components
- `_common/parameters.yaml` is defined but not referenced by any entrypoint
- **Status:** No action required (may be used in future)

### Files with No External Dependencies
- `health.yaml` - No `$ref` entries to `_common/` (standalone file)
- **Status:** Will bundle cleanly without external resolution

## Dependency Summary by Entrypoint

### `auth.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `responses` (Unauthorized, TooManyRequests, InternalServerError), `securitySchemes` (BearerAuth)
- **Total External Refs:** 10

### `attribution.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `responses` (Unauthorized, TooManyRequests, InternalServerError), `securitySchemes` (BearerAuth)
- **Total External Refs:** 4
- **Issue:** Contains inline schema that needs extraction

### `reconciliation.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `responses` (Unauthorized, TooManyRequests, InternalServerError), `securitySchemes` (BearerAuth)
- **Total External Refs:** 4

### `export.yaml`
- **Dependencies:** `_common/components.yaml`, `_common/pagination.yaml`
- **Components Used:** 
  - From `components.yaml`: `responses` (Unauthorized, TooManyRequests, InternalServerError), `securitySchemes` (BearerAuth)
  - From `pagination.yaml`: `parameters` (limit, cursor)
- **Total External Refs:** 6

### `health.yaml`
- **Dependencies:** None
- **Total External Refs:** 0

### `webhooks/shopify.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `schemas` (Problem), `responses` (Unauthorized)
- **Total External Refs:** 2

### `webhooks/woocommerce.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `schemas` (Problem), `responses` (Unauthorized)
- **Total External Refs:** 2

### `webhooks/stripe.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `schemas` (Problem), `responses` (Unauthorized)
- **Total External Refs:** 2

### `webhooks/paypal.yaml`
- **Dependencies:** `_common/components.yaml` only
- **Components Used:** `schemas` (Problem), `responses` (Unauthorized)
- **Total External Refs:** 2

## Bundling Readiness Assessment

All entrypoints use consistent `$ref` patterns that should resolve correctly with Redocly CLI bundling. The only known issue is the inline schema in `attribution.yaml` which will be addressed in Phase 3.

**Total Entrypoints:** 9 (5 domain + 4 webhook)
**Entrypoints with Dependencies:** 8 (all except `health.yaml`)
**Common Files Referenced:** 2 (`components.yaml`, `pagination.yaml`)





