# Documentation Index

## 🚀 Quick Navigation

**First time here?** Start with **[GOVERNANCE_INDEX.md](GOVERNANCE_INDEX.md)** - entry point for all governance rules

**Looking for API docs?** See [API Contracts](#api-contracts) below

**Need implementation guides?** See [Implementation Guides](#implementation-guides) below

---

## Governance Framework

**[GOVERNANCE_INDEX.md](GOVERNANCE_INDEX.md)** - Central navigation for all governance rules across 4 layers:
- Database governance (db/)
- API contract governance (api-contracts/governance/)
- Validation scripts (scripts/governance/)
- Policy documentation (docs/governance/)

This is your entry point for understanding SKELDIR 2.0 architectural rules.

---

## Skeldir API Documentation

This directory contains configuration for serving API documentation from OpenAPI contracts.

## Local Development

### Using Redoc

1. Install Redoc CLI:
```bash
npm install -g @redocly/cli
```

2. Serve documentation:
```bash
redocly preview-docs api-contracts/openapi/v1/auth.yaml
```

### Using Swagger UI

1. Install Swagger UI:
```bash
npm install -g swagger-ui-serve
```

2. Serve documentation:
```bash
swagger-ui-serve api-contracts/openapi/v1/auth.yaml
```

## Production Deployment

Documentation will be served from `/docs` endpoint in production, aggregating all domain contracts.

## Contract Files

All API contracts are located in `api-contracts/openapi/v1/`:
- Domain APIs: `auth.yaml`, `attribution.yaml`, `reconciliation.yaml`, `export.yaml`, `health.yaml`
- Webhooks: `webhooks/shopify.yaml`, `webhooks/woocommerce.yaml`, `webhooks/stripe.yaml`, `webhooks/paypal.yaml`
- Common components: `_common/components.yaml`, `_common/pagination.yaml`, `_common/parameters.yaml`











