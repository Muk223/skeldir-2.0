# SKELDIR 2.0 Development Workflow

This document describes the contract-first development workflow in the monorepo context.

## Workflow Overview

SKELDIR follows a **contract-first** development approach where OpenAPI specifications are defined before implementation. This ensures:

- API contracts serve as the immutable source of truth
- Frontend and backend teams can work in parallel
- Breaking changes are detected automatically
- Integration is validated continuously

## Development Process

### 1. Define Contract

Create or update OpenAPI specification in `contracts/openapi/v1/`:

```bash
# Edit contract file
vim contracts/openapi/v1/attribution.yaml
```

**Requirements:**
- Use OpenAPI 3.1.0
- Include all required fields (X-Correlation-ID header, tenant_id in responses)
- Follow existing contract structure and patterns
- Reference shared components from `_common/`

### 2. Validate Contract

Validate the contract structure:

```bash
# Validate single file
openapi-generator-cli validate -i contracts/openapi/v1/attribution.yaml

# Validate all contracts
make contracts-validate
```

**CI Check:** Contracts are automatically validated on every push/PR.

### 3. Check for Breaking Changes

If modifying existing contracts, check for breaking changes:

```bash
# CI automatically runs oasdiff breaking
# Check baseline comparison in contracts/baselines/v1.0.0/
```

**Breaking Change Policy:**
- Breaking changes require major version bump
- Migration guide must be published 30 days before deployment
- CI will fail if breaking changes detected without version bump

### 4. Generate Pydantic Models

Generate Python Pydantic models from contracts:

```bash
make models-generate
# or
bash scripts/generate-models.sh
```

**Output:** Models are generated in `backend/app/schemas/`

**Note:** Models are auto-generated. Do not edit manually. Regenerate after contract changes.

### 5. Implement Backend

Implement the endpoint in `backend/app/`:

```python
# backend/app/api/v1/attribution.py
from fastapi import APIRouter, Depends, Header
from backend.app.schemas.attribution import YourResponseModel
from backend.app.core.auth import get_current_tenant

router = APIRouter(prefix="/api/attribution", tags=["Attribution"])

@router.get("/your-endpoint", response_model=YourResponseModel)
async def your_endpoint(
    correlation_id: str = Header(..., alias="X-Correlation-ID"),
    tenant_id: str = Depends(get_current_tenant),
):
    # Implementation
    pass
```

**Requirements:**
- Use generated Pydantic models
- Require X-Correlation-ID header
- Inject tenant_id via dependency
- Follow patterns in `.cursor/rules`

### 6. Write Backend Tests

Write unit tests in `backend/tests/`:

```python
# backend/tests/test_attribution.py
import pytest
from backend.app.api.v1.attribution import your_endpoint

def test_your_endpoint():
    # Test implementation
    pass
```

**Run Tests:**
```bash
cd backend
pytest
```

### 7. Update Frontend SDK

If contracts changed, regenerate frontend SDK:

```bash
# Generate TypeScript SDK from contracts
npm run generate-sdk
```

**Output:** SDK generated in `frontend/src/generated/api/`

### 8. Update Frontend

Update frontend code to use new/updated endpoints:

```typescript
// frontend/src/components/YourComponent.tsx
import { YourApiClient } from '@/generated/api/attribution';

const client = new YourApiClient();
const data = await client.yourEndpoint();
```

### 9. Test Integration

Run integration tests against mock servers:

```bash
# Start mock servers
make mocks-start

# Run integration tests
make tests-integration
# or
npm test
```

**Integration Tests:**
- Playwright tests in `tests/`
- Test against Prism mock servers
- Validate contract compliance

### 10. Submit Pull Request

Create PR with:

- Contract changes (if any)
- Backend implementation
- Frontend updates (if any)
- Tests (unit + integration)
- Documentation updates

**PR Requirements:**
- All tests pass
- Contracts validate
- No breaking changes (unless major version bump)
- CI checks pass

## Local Development Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- Git

### Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd skeldir-2.0

# Install root dependencies
npm install

# Setup backend
cd backend
pip install -r requirements.txt
alembic upgrade head

# Setup frontend
cd ../frontend
npm install
```

### Daily Workflow

```bash
# Start mock servers (for frontend development)
make mocks-start

# Run backend tests
cd backend && pytest

# Run frontend tests
cd frontend && npm test

# Run integration tests
make tests-integration
```

## Contract-First Benefits

### Parallel Development

- Frontend team can develop against mock servers while backend is being implemented
- Backend team has clear contract requirements before implementation
- Both teams work from the same source of truth

### Automatic Validation

- CI validates contracts on every change
- Breaking changes are detected automatically
- Integration tests validate contract compliance

### Documentation

- Contracts serve as living documentation
- API documentation is auto-generated from contracts
- No manual documentation drift

## Common Tasks

### Adding a New Endpoint

1. Add endpoint to contract in `contracts/openapi/v1/`
2. Validate contract
3. Generate models: `make models-generate`
4. Implement in `backend/app/`
5. Write tests
6. Update frontend SDK
7. Update frontend code
8. Test integration

### Modifying an Existing Endpoint

1. Check if change is breaking (requires version bump)
2. Update contract
3. Validate and check breaking changes
4. Regenerate models
5. Update backend implementation
6. Update tests
7. Update frontend SDK and code
8. Test integration

### Fixing a Bug

1. Identify bug in contract, backend, or frontend
2. Fix the issue
3. Add/update tests
4. Ensure all tests pass
5. Submit PR

## Best Practices

1. **Always define contracts first** - Don't implement before contract is defined
2. **Validate early and often** - Run validation locally before pushing
3. **Write tests** - Unit tests for backend, integration tests for E2E
4. **Keep contracts in sync** - Update contracts when implementation changes
5. **Document breaking changes** - Use migration template for major versions
6. **Test integration** - Always run integration tests before merging

## Troubleshooting

### Models not generating

- Check contract syntax: `openapi-generator-cli validate -i contracts/openapi/v1/your-file.yaml`
- Ensure datamodel-codegen is installed: `pip install datamodel-code-generator[openapi]`

### Mock servers not starting

- Check Docker is running: `docker ps`
- Check ports are available: `netstat -an | grep 4010`
- View logs: `./scripts/view-logs.sh all`

### Integration tests failing

- Ensure mock servers are running: `make mocks-start`
- Check test configuration in `playwright.config.ts`
- View test output: `npm test -- --reporter=list`

## Additional Resources

- [Monorepo Structure](MONOREPO_STRUCTURE.md)
- [CI/CD Documentation](CI_CD.md)
- [Contract Documentation](../contracts/README.md)
- [Contributing Guide](CONTRIBUTING.md)

