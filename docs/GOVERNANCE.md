# Governance Model

This document defines the governance model for Skeldir API Contracts, including contract ownership, change process, and versioning protocol.

## Contract Ownership

### Primary Owners

- **Backend Team Leads**: Own all contract changes in `api-contracts/`
- **Architecture Lead**: Final approval authority for breaking changes
- **Frontend Lead**: Required reviewer for breaking changes (SDK/FE impact)

### Ownership Scope

- **Contracts**: Backend team leads own all OpenAPI specifications
- **CI/CD Workflows**: Backend team leads own CI configuration
- **Documentation**: Backend team leads own contract documentation
- **Breaking Changes**: Require architecture lead approval + FE lead review

## Change Process

### Standard Change Workflow

1. **Proposal**: Create issue using appropriate template
2. **Discussion**: Get feedback from relevant stakeholders
3. **Implementation**: Update OpenAPI specification
4. **Validation**: Local validation and breaking change check
5. **PR Submission**: Create pull request with changes
6. **CI Validation**: Automated CI checks (validation, breaking changes, semver)
7. **CODEOWNERS Review**: Backend team leads review changes
8. **Approval**: At least one CODEOWNER approval required
9. **Merge**: Squash or rebase merge (linear history required)

### Breaking Change Workflow

1. **Proposal**: Create issue with breaking change template
2. **Impact Assessment**: Document breaking changes and migration path
3. **Migration Guide**: Create migration guide (30-day notice period)
4. **Stakeholder Review**: Architecture lead + FE lead review
5. **Approval**: Architecture lead final approval
6. **Version Bump**: Major version increment (e.g., `1.0.0` → `2.0.0`)
7. **PR Submission**: Create pull request with breaking changes
8. **CI Validation**: CI detects breaking changes (must be intentional)
9. **Review & Merge**: All approvals required before merge

## Versioning Protocol

### Semantic Versioning

Contracts follow [Semantic Versioning](https://semver.org/) (`major.minor.patch`):

- **Major** (`x.0.0`): Breaking changes requiring migration guide
- **Minor** (`x.y.0`): Additive changes (new endpoints, optional fields)
- **Patch** (`x.y.z`): Documentation updates, non-breaking fixes

### Version Bump Rules

| Change Type | Version Bump | Approval Required |
|------------|--------------|-------------------|
| Breaking change | Major | Architecture lead + FE lead |
| New endpoint | Minor | Backend team lead |
| Optional field added | Minor | Backend team lead |
| Documentation fix | Patch | Backend team lead |
| Typo fix | Patch | Backend team lead |

### Version Enforcement

- **CI Enforcement**: CI validates semver format in all contracts
- **Consistency**: All contracts in same version must have same `info.version`
- **Baseline Comparison**: Breaking changes detected via `oasdiff` against baseline

## Breaking Change Authority

### What Requires Architecture Lead Approval?

- Major version bumps (`x.0.0`)
- Endpoint removals
- Required field removals
- Type changes
- Authentication requirement changes
- Path or method changes

### Migration Guide Requirements

Breaking changes require:

1. **Migration Guide**: Document in `api-contracts/MIGRATION_TEMPLATE.md`
2. **30-Day Notice**: Migration guide published 30 days before deployment
3. **Deprecation Period**: Old version supported during migration period
4. **Stakeholder Communication**: Notify all consumers (FE, SDK, integrations)

## FE/Prism Port Mapping

### Expected Port Assignments

Contracts include Prism mock server URLs for frontend development:

- **Auth**: `http://localhost:4010`
- **Attribution**: `http://localhost:4011`
- **Reconciliation**: `http://localhost:4012`
- **Export**: `http://localhost:4013`
- **Health**: `http://localhost:4014`
- **Shopify Webhook**: `http://localhost:4015`
- **WooCommerce Webhook**: `http://localhost:4016`
- **Stripe Webhook**: `http://localhost:4017`
- **PayPal Webhook**: `http://localhost:4018`

### Port Mapping Expectations

- **Stability**: Port assignments are stable and should not change
- **FE Dependency**: Frontend team depends on these ports for Prism mocks
- **Breaking Change**: Changing port assignments requires FE lead approval

## Code Review Process

### Review Requirements

- **CODEOWNERS**: At least one backend team lead must approve
- **Breaking Changes**: Architecture lead + FE lead must approve
- **CI Checks**: All CI checks must pass before merge
- **Linear History**: No merge commits (squash or rebase only)

### Review Checklist

- [ ] Contract passes OpenAPI validation
- [ ] No breaking changes (or breaking changes approved)
- [ ] Version bumped appropriately
- [ ] Privacy constraints documented (webhooks)
- [ ] Examples included (new endpoints)
- [ ] Documentation updated

## Dispute Resolution

### Escalation Path

1. **Technical Disagreement**: Escalate to architecture lead
2. **Breaking Change Dispute**: Architecture lead makes final decision
3. **FE Impact Dispute**: FE lead provides final assessment
4. **Security Concern**: Escalate to security team

### Decision Authority

- **Architecture Lead**: Final authority on breaking changes
- **Backend Team Leads**: Authority on additive changes
- **Security Team**: Authority on security-related changes

## Change Communication

### Internal Communication

- **Breaking Changes**: Notify FE team, SDK team, and integrations team
- **Additive Changes**: Notify relevant teams via PR description
- **Security Updates**: Notify security team and compliance team

### External Communication

- **Public Documentation**: Update README and CHANGELOG
- **Migration Guides**: Publish migration guides for breaking changes
- **Release Notes**: Include in GitHub releases

## Compliance and Audit

### Audit Requirements

- **Change History**: All changes tracked via Git history
- **Approval Trail**: PR reviews provide approval trail
- **CI Logs**: CI logs provide validation evidence
- **Documentation**: All changes documented in CHANGELOG

### Acquisition Readiness

Repository governance supports acquisition due diligence:

- **Clear Ownership**: CODEOWNERS defines ownership
- **Change Process**: Documented and enforced
- **Audit Trail**: Git history + PR reviews + CI logs
- **Professional Standards**: Security policies, privacy notes, governance docs

## References

- [CONTRIBUTING.md](CONTRIBUTING.md): Contribution workflow
- [SECURITY.md](../SECURITY.md): Security policy
- [PRIVACY-NOTES.md](../PRIVACY-NOTES.md): Privacy constraints
- [CHANGELOG.md](../CHANGELOG.md): Version history

