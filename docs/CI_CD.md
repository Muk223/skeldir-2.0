# CI/CD Documentation

This document describes the continuous integration and deployment pipeline for SKELDIR 2.0 monorepo.

## Overview

The monorepo uses a unified CI/CD pipeline that validates contracts, backend, and frontend in a single workflow with a single git checkout (Schmidt's key requirement).

## Pipeline Structure

### Single Git Checkout

All jobs use a single git checkout, ensuring:

- Atomic versioning (single commit hash versions all components)
- Simplified workflow (no multi-repo coordination)
- Prevented contract drift (architecturally impossible for components to be out of sync)

### Workflow Jobs

#### 1. Checkout Code

Single git checkout with full history for versioning.

#### 2. Validate Contracts

Validates all OpenAPI 3.1.0 contract files:

- Structural validation
- Syntax checking
- Schema validation

**Triggers:** On changes to `contracts/**/*.yaml`

#### 3. Test Backend

Runs backend unit tests:

- pytest test suite
- Coverage reporting
- Type checking (mypy)

**Triggers:** On changes to `backend/`

**Status:** Will activate when backend code is migrated

#### 4. Test Frontend

Runs frontend tests:

- Unit tests
- Component tests
- Linting

**Triggers:** On changes to `frontend/`

**Status:** Will activate when frontend code is migrated

#### 5. Integration Tests

Runs Playwright integration tests:

- Starts Prism mock servers
- Runs E2E tests against mocks
- Validates contract compliance

**Triggers:** On every push/PR

#### 6. Generate Models

Generates Pydantic models from contracts:

- Runs `scripts/generate-models.sh`
- Verifies model generation
- Tests model imports

**Triggers:** On changes to `contracts/`

## Workflow Files

### `.github/workflows/ci.yml`

Unified CI pipeline that:

- Validates contracts
- Tests backend (when available)
- Tests frontend (when available)
- Runs integration tests
- Generates models

### `.github/workflows/contract-validation.yml`

Specialized contract validation workflow:

- OpenAPI structural validation
- Breaking change detection (`oasdiff`)
- Semantic versioning enforcement
- Model generation verification

### `.github/workflows/contract-publish.yml`

Contract release workflow:

- Tags releases with version number
- Creates GitHub releases
- Publishes contract artifacts

## Atomic Versioning

All components are versioned together:

- **Single Commit Hash**: One commit versions contracts, backend, and frontend
- **Single Version Number**: One version number applies to all components
- **Synchronized Releases**: All components released together

## Breaking Change Detection

Breaking changes are detected automatically:

1. Compare current contracts with baselines in `contracts/baselines/v1.0.0/`
2. Run `oasdiff breaking` to detect breaking changes
3. Fail CI if breaking changes detected without major version bump
4. Require migration guide for major version bumps

## Model Generation

Pydantic models are auto-generated in CI:

1. Run `scripts/generate-models.sh`
2. Generate models in `backend/app/schemas/`
3. Verify models can be imported
4. Fail CI if generation fails

## Integration Testing

Integration tests validate end-to-end behavior:

1. Start Prism mock servers via Docker Compose
2. Wait for services to be healthy
3. Run Playwright tests against mocks
4. Validate contract compliance
5. Stop services after tests

## Deployment

Deployment is triggered by:

- Tags matching `v*.*.*` pattern
- Manual workflow dispatch
- Push to `main` branch (for contract releases)

## Status Badges

Add status badges to README:

```markdown
[![CI Status](https://github.com/org/repo/workflows/CI/badge.svg)](https://github.com/org/repo/actions)
```

## Local Testing

Test CI workflows locally:

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
choco install act-cli  # Windows

# Run workflow
act -j validate-contracts
```

## Troubleshooting

### CI Failing on Contract Validation

- Check contract syntax: `openapi-generator-cli validate -i contracts/openapi/v1/your-file.yaml`
- Verify all referenced components exist
- Check for YAML syntax errors

### Integration Tests Failing

- Ensure Docker is available in CI
- Check mock server health checks
- Verify Playwright configuration

### Model Generation Failing

- Check datamodel-codegen is installed
- Verify contract structure
- Check Python version (3.11+)

## Best Practices

1. **Run CI locally first** - Use act or similar tools
2. **Fix failing tests immediately** - Don't let CI failures accumulate
3. **Keep workflows simple** - Single responsibility per job
4. **Use conditional jobs** - Only run when relevant files change
5. **Cache dependencies** - Speed up CI runs

## Future Enhancements

- Add backend deployment workflow
- Add frontend deployment workflow
- Add database migration validation
- Add performance testing
- Add security scanning

