# Contract Change Pull Request

## Description

Brief description of the contract changes in this PR.

## Change Type

- [ ] Breaking change (major version bump)
- [ ] Additive change (minor version bump)
- [ ] Documentation update (patch version bump)

## Contract Files Modified

- `api-contracts/openapi/v1/[domain].yaml`
- `api-contracts/openapi/v1/[other-domain].yaml`

## Checklist

### Validation

- [ ] Contract passes local validation (`openapi-generator-cli validate`)
- [ ] No breaking changes detected (or breaking changes are intentional)
- [ ] Version bumped appropriately (semver)
- [ ] All CI checks pass

### Documentation

- [ ] README updated (if needed)
- [ ] CHANGELOG.md updated
- [ ] Migration guide created (if breaking change)
- [ ] Privacy constraints documented (for webhooks)

### Examples

- [ ] Examples included for new endpoints
- [ ] Error examples updated (if needed)
- [ ] Request/response examples complete

### Review

- [ ] CODEOWNERS notified
- [ ] FE lead notified (if breaking change or FE impact)
- [ ] Architecture lead notified (if breaking change)

## Breaking Changes (if applicable)

### Migration Guide

- [ ] Migration guide created: `api-contracts/MIGRATION_TEMPLATE.md`
- [ ] 30-day notice period planned
- [ ] Stakeholders notified

### Impact Summary

- Endpoints removed: `[list]`
- Fields removed: `[list]`
- Type changes: `[list]`
- Other breaking changes: `[describe]`

## FE Impact Assessment

- [ ] Requires frontend SDK changes
- [ ] Requires frontend API integration changes
- [ ] No frontend impact

## Testing Evidence

- Local validation output: `[paste output]`
- Breaking change check: `[paste output]`
- Model generation: `[paste output]`

## Related Issues

Closes #[issue-number]

## Additional Context

Add any other context, screenshots, or examples about the PR.

