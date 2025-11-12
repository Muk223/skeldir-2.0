# Changelog

All notable changes to Skeldir API Contracts will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-10

### Added

- Initial OpenAPI 3.1.0 contract specifications for B0.1 milestone
- Authentication API (`auth.yaml`) with login, refresh token, and logout endpoints
- Attribution API (`attribution.yaml`) with realtime revenue endpoint
- Reconciliation API (`reconciliation.yaml`) with pipeline status endpoint
- Export API (`export.yaml`) with revenue export endpoint (CSV/JSON formats)
- Health check API (`health.yaml`) with unauthenticated health endpoint
- Webhook APIs for commerce platforms:
  - Shopify order creation webhook (`webhooks/shopify.yaml`)
  - WooCommerce order creation webhook (`webhooks/woocommerce.yaml`)
  - Stripe charge succeeded webhook (`webhooks/stripe.yaml`)
  - PayPal sale completed webhook (`webhooks/paypal.yaml`)
- Common components (`_common/components.yaml`):
  - BearerAuth security scheme (JWT)
  - X-Correlation-ID header (UUID format)
  - Rate limit headers (X-RateLimit-*)
  - RFC7807 Problem schema with Skeldir extensions (error_id, correlation_id)
  - Shared error responses (401 Unauthorized, 429 Too Many Requests, 500 Internal Server Error)
- Pagination components (`_common/pagination.yaml`):
  - Cursor-based pagination parameters (limit, cursor)
  - PaginationMeta envelope schema
- Parameter components (`_common/parameters.yaml`):
  - Idempotency key parameter
  - Tenant ID parameter
- Prism mock server URLs for frontend development (ports 4010-4018)
- CI/CD workflows:
  - OpenAPI validation workflow
  - Breaking change detection workflow (`oasdiff`)
  - Semantic versioning enforcement workflow
  - Pydantic model generation workflow
  - Contract publish workflow (tags releases)
- Baseline freeze (`baselines/v1.0.0/`) for breaking change detection
- Documentation:
  - Root README with Quick Start guide
  - API contracts README with usage instructions
  - Security policy (SECURITY.md)
  - Privacy notes (PRIVACY-NOTES.md)
  - Contributing guide (docs/CONTRIBUTING.md)
  - Governance model (docs/GOVERNANCE.md)
- Repository infrastructure:
  - CODEOWNERS file for contract ownership
  - Dependabot configuration for security updates
  - Issue templates (bug report, feature request, contract change)
  - Pull request template

### Security

- All webhook endpoints include explicit PII-stripping statements
- Session-scoped data only (30-minute inactivity timeout)
- Tenant isolation enforced via `tenant_id` in authenticated responses
- HMAC signature validation required for all webhooks
- No PII exposure in contract schemas

### Documentation

- Comprehensive API contract documentation
- Privacy constraints documented in all webhook schemas
- Contract-first development workflow documented
- Governance model established

---

## [Unreleased]

### Added - Monorepo Migration (2025-11-12)

- **Monorepo Structure**: Migrated to unified monorepo containing contracts, backend, and frontend
- **Directory Structure**:
  - `contracts/` - OpenAPI 3.1.0 contract specifications (migrated from `api-contracts/`)
  - `backend/` - FastAPI application structure (prepared for code migration)
  - `frontend/` - Replit UI structure (prepared for code migration)
  - `docs/` - Consolidated documentation including database governance
- **Database Infrastructure**: Migrated to `backend/db/` and `backend/alembic/`
- **Unified CI/CD**: Single git checkout pipeline (`.github/workflows/ci.yml`)
- **Root Configuration**: Added `Makefile` and `package.json` for monorepo management
- **Documentation**:
  - `docs/MONOREPO_STRUCTURE.md` - Monorepo organization guide
  - `docs/DEVELOPMENT_WORKFLOW.md` - Contract-first workflow in monorepo context
  - `docs/CI_CD.md` - CI/CD pipeline documentation
- **Atomic Versioning**: Single commit hash now versions all components simultaneously
- **Script Updates**: All scripts updated to reference `contracts/` instead of `api-contracts/`
- **Docker Compose**: Unified `docker-compose.yml` with updated paths

### Changed

- Contract directory: `api-contracts/` → `contracts/`
- Database migrations: `db/migrations/` → `backend/db/migrations/`
- Database docs: `db/docs/` → `docs/database/`
- Alembic: Root → `backend/alembic/`
- Model generation output: `app/schemas/` → `backend/app/schemas/`
- Docker Compose: `docker-compose.mock.yml` → `docker-compose.yml` (unified)

### Planned

- GitHub Pages deployment for live API documentation
- Additional webhook platforms (as needed)
- Enhanced error response examples
- OpenAPI contract examples for common use cases
- Backend code migration (when available)
- Frontend code migration (when available)

---

## Version History

- **1.0.0** (2025-11-10): Initial contract release for B0.1 milestone

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

