# SKELDIR 2.0 Monorepo Structure

This document explains the folder organization and structure of the SKELDIR 2.0 monorepo.

## Overview

The monorepo contains all components of the Skeldir Attribution Intelligence platform in a single repository, enabling atomic versioning and simplified CI/CD.

## Directory Structure

```
.
├── backend/          # FastAPI application (modular monolith)
│   ├── app/          # Application code
│   │   ├── ingestion/    # Event ingestion service
│   │   ├── attribution/  # Statistical attribution models
│   │   ├── auth/         # Authentication and authorization
│   │   └── webhooks/     # Webhook handlers
│   ├── db/            # Database infrastructure
│   │   ├── migrations/   # Alembic migrations
│   │   ├── seeds/        # Seed data
│   │   └── snapshots/    # Schema snapshots
│   ├── alembic/       # Alembic configuration
│   ├── tests/         # Backend unit tests
│   └── requirements.txt
│
├── frontend/         # Replit UI (to be migrated)
│   ├── src/           # Frontend source code
│   ├── public/        # Static assets
│   └── package.json
│
├── contracts/        # OpenAPI 3.1.0 contract specifications
│   ├── openapi/v1/    # Version 1 API contracts
│   │   ├── _common/   # Shared components
│   │   ├── auth.yaml
│   │   ├── attribution.yaml
│   │   ├── reconciliation.yaml
│   │   ├── export.yaml
│   │   ├── health.yaml
│   │   └── webhooks/  # Webhook contracts
│   └── baselines/     # Frozen baselines for breaking change detection
│
├── docs/             # Shared documentation
│   ├── database/      # Database governance documentation
│   ├── MONOREPO_STRUCTURE.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   └── CI_CD.md
│
├── scripts/          # Shared utility scripts
│   ├── generate-models.sh
│   ├── start-mocks.sh
│   ├── stop-mocks.sh
│   └── ...
│
├── tests/            # Integration tests (Playwright)
│   └── frontend-integration.spec.ts
│
├── .github/          # CI/CD workflows
│   └── workflows/
│       ├── ci.yml
│       ├── contract-validation.yml
│       └── contract-publish.yml
│
├── docker-compose.yml # Unified Docker Compose (mock servers + future services)
├── playwright.config.ts
└── README.md
```

## Component Responsibilities

### `backend/`

Contains the FastAPI application implementing the Skeldir Attribution Intelligence backend:

- **Modular Monolith**: Structured as separate modules (ingestion, attribution, auth, webhooks) with clear boundaries
- **Database**: All database-related code (migrations, seeds, snapshots) lives here
- **Tests**: Backend unit tests are co-located with the code they test

### `frontend/`

Contains the Replit UI frontend application:

- **Source Code**: React/TypeScript application code
- **Generated SDK**: TypeScript SDK generated from OpenAPI contracts
- **Tests**: Frontend unit and integration tests

### `contracts/`

Contains OpenAPI 3.1.0 contract specifications:

- **Source of Truth**: Contracts are defined before implementation (contract-first)
- **Baselines**: Frozen versions for breaking change detection
- **Versioning**: Follows semantic versioning (major.minor.patch)

### `docs/`

Shared documentation across all components:

- **Database**: Database governance, migration guides, schema documentation
- **Monorepo**: Structure, workflow, and contribution guides
- **CI/CD**: Continuous integration and deployment documentation

### `scripts/`

Shared utility scripts used across components:

- **Model Generation**: Generate Pydantic models from contracts
- **Mock Servers**: Start/stop Prism mock servers
- **Validation**: Contract and integration test scripts

### `tests/`

Integration tests that test cross-component behavior:

- **Playwright**: End-to-end tests against Prism mock servers
- **Contract Testing**: Validates API responses match contracts

## Design Principles

### 1. Atomic Versioning

All components (contracts, backend, frontend) are versioned together via a single commit hash. This ensures:

- No version drift between components
- Single source of truth for what version is deployed
- Simplified release process

### 2. Contract-First Development

Contracts are defined before implementation:

1. Define contract in `contracts/openapi/v1/`
2. Generate Pydantic models
3. Implement backend
4. Update frontend SDK
5. Test integration

### 3. Component Isolation

Each component is self-contained:

- Backend has its own tests, dependencies, and configuration
- Frontend has its own tests, dependencies, and configuration
- Contracts are independent and can be validated separately

### 4. Shared Infrastructure

Common infrastructure is shared:

- Documentation in `docs/`
- Scripts in `scripts/`
- Integration tests in `tests/`
- CI/CD workflows in `.github/workflows/`

## Migration Notes

This monorepo was created by migrating:

- **Contracts**: From `api-contracts/` → `contracts/`
- **Database**: From `db/` → `backend/db/`, docs → `docs/database/`
- **Alembic**: From root → `backend/alembic/`
- **Tests**: Already at root level (no migration needed)

## Future Additions

When backend and frontend code are migrated:

- Backend code will be placed in `backend/app/`
- Frontend code will be placed in `frontend/src/`
- Additional tests will be added to component-specific test directories

