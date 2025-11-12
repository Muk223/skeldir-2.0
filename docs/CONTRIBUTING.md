# Contributing to Skeldir API Contracts

Thank you for your interest in contributing to Skeldir API Contracts! This guide outlines the contract-first development workflow and contribution process.

## Contract-First Development Workflow

Skeldir follows a **contract-first** approach where OpenAPI specifications are defined before implementation. This ensures:

- API stability and consistency
- Automated model generation
- Breaking change detection
- Clear API documentation

### Workflow Steps

1. **Define Contract**: Create or modify OpenAPI 3.1.0 specification in `api-contracts/openapi/v1/`
2. **Validate Locally**: Run `openapi-generator-cli validate -i api-contracts/openapi/v1/[domain].yaml`
3. **Generate Models**: Run `bash scripts/generate-models.sh` to generate Pydantic models
4. **Test Breaking Changes**: Run `oasdiff breaking baselines/v1.0.0/ api-contracts/openapi/v1/`
5. **Create PR**: Submit pull request with contract changes
6. **CI Validation**: CI automatically validates contracts and detects breaking changes
7. **Review & Merge**: CODEOWNERS review and approve changes

## How to Propose Changes

### For New Endpoints or Fields

1. **Create Issue**: Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
2. **Discuss**: Get feedback from backend team leads and frontend lead (if breaking change)
3. **Update Contract**: Modify or create OpenAPI specification
4. **Validate**: Ensure contract passes local validation
5. **Create PR**: Submit pull request with contract changes

### For Bug Fixes

1. **Create Issue**: Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
2. **Fix Contract**: Update OpenAPI specification to fix the bug
3. **Validate**: Ensure contract passes local validation
4. **Create PR**: Submit pull request with fix

### For Contract Modifications

1. **Create Issue**: Use the [contract change template](.github/ISSUE_TEMPLATE/contract_change.md)
2. **Determine Impact**: Classify as breaking or additive change
3. **Update Contract**: Modify OpenAPI specification
4. **Update Version**: Bump version according to [semantic versioning](https://semver.org/)
5. **Create PR**: Submit pull request with changes

## Breaking Change Protocol

### What Constitutes a Breaking Change?

- Removing an endpoint
- Removing a required field
- Changing a field type
- Changing an endpoint path or HTTP method
- Making an optional field required
- Changing authentication requirements

### Breaking Change Process

1. **Major Version Bump**: Update `info.version` to next major version (e.g., `1.0.0` → `2.0.0`)
2. **Migration Guide**: Create migration guide in `api-contracts/MIGRATION_TEMPLATE.md`
3. **30-Day Notice**: Migration guide must be published 30 days before deployment
4. **FE Lead Review**: Frontend lead must review breaking changes for SDK/FE impact
5. **Architecture Approval**: Architecture lead must approve breaking changes

### Additive Changes (Minor Version)

- Adding a new endpoint
- Adding an optional field
- Adding a new response code
- Adding new query parameters

**Process**: Bump minor version (e.g., `1.0.0` → `1.1.0`)

### Documentation Updates (Patch Version)

- Fixing typos
- Improving descriptions
- Adding examples
- Clarifying documentation

**Process**: Bump patch version (e.g., `1.0.0` → `1.0.1`)

## Pull Request Process

### PR Checklist

- [ ] Contract passes local validation (`openapi-generator-cli validate`)
- [ ] No breaking changes (or breaking changes approved with migration guide)
- [ ] Version bumped appropriately (semver)
- [ ] All CI checks pass
- [ ] Documentation updated (if needed)
- [ ] Privacy constraints documented (for webhooks)
- [ ] Examples included for new endpoints

### PR Template

When creating a PR, use the [pull request template](.github/PULL_REQUEST_TEMPLATE.md) which includes:

- Description of changes
- Breaking change indicator
- FE impact assessment
- Migration guide link (if breaking)
- Testing evidence

### Review Process

1. **Automated Checks**: CI validates contracts and detects breaking changes
2. **CODEOWNERS Review**: Backend team leads review contract changes
3. **FE Review**: Frontend lead reviews breaking changes for SDK/FE impact
4. **Approval**: At least one CODEOWNER approval required
5. **Merge**: Squash or rebase merge (linear history required)

## Code Style and Standards

### OpenAPI 3.1.0 Specification

- Use OpenAPI 3.1.0 format (`openapi: 3.1.0`)
- Follow [OpenAPI Specification](https://spec.openapi.org/oas/v3.1.0) guidelines
- Use semantic versioning for `info.version`

### Naming Conventions

- **Operation IDs**: Use camelCase (e.g., `getRealtimeRevenue`)
- **Schema Names**: Use PascalCase (e.g., `RevenueResponse`)
- **Parameter Names**: Use camelCase (e.g., `tenantId`)
- **Header Names**: Use kebab-case with X- prefix (e.g., `X-Correlation-ID`)

### DRY Principles

- **No Duplication**: Use `$ref` to reference `_common` components
- **Shared Components**: Define reusable components in `_common/components.yaml`
- **Consistent Patterns**: Follow existing patterns for similar endpoints

### Privacy Constraints

- **Webhook Privacy**: All webhook endpoints must include explicit PII-stripping statements
- **Session Scoping**: Document session-scoped data constraints
- **No PII**: Never expose PII in contract schemas

## Local Development Setup

### Prerequisites

```bash
# Node.js 20+ for OpenAPI validation
npm install -g @openapitools/openapi-generator-cli

# Python 3.11+ for Pydantic model generation
pip install datamodel-code-generator[openapi] pydantic>=2.0.0

# Go 1.21+ for breaking change detection (optional)
go install github.com/Tufin/oasdiff@latest
```

### Validation Commands

```bash
# Validate all contracts
openapi-generator-cli validate -i api-contracts/openapi/v1/*.yaml

# Generate Pydantic models
bash scripts/generate-models.sh

# Check breaking changes
oasdiff breaking api-contracts/baselines/v1.0.0/ api-contracts/openapi/v1/
```

## Approval Authority

### Contract Ownership

- **Backend Team Leads**: Own all contract changes (`api-contracts/`)
- **Frontend Lead**: Required reviewer for breaking changes
- **Architecture Lead**: Final approval for breaking changes

### Change Authority

- **Additive Changes**: Backend team leads can approve
- **Breaking Changes**: Require architecture lead approval + FE lead review
- **Security Changes**: Require security team review

## Questions?

- Review [GOVERNANCE.md](GOVERNANCE.md) for contract ownership and change process
- Check [SECURITY.md](../SECURITY.md) for security policy
- See [PRIVACY-NOTES.md](../PRIVACY-NOTES.md) for privacy constraints
- Open an issue using the appropriate template

Thank you for contributing to Skeldir API Contracts!

