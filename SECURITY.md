# Security Policy

## Supported Versions

We actively support the following contract versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Skeldir API contracts seriously. If you discover a security vulnerability in our OpenAPI specifications or contract definitions, please report it responsibly.

### How to Report

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email security concerns to: **security@skeldir.com** (or your designated security contact)
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce (if applicable)
   - Potential impact
   - Suggested fix (if available)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Timeline**: Depends on severity (typically 30-90 days for critical issues)

### Security Best Practices

Our contracts follow these security principles:

- **No PII Exposure**: All webhook endpoints include explicit PII-stripping statements
- **Authentication Required**: All authenticated endpoints require JWT Bearer tokens
- **Rate Limiting**: All endpoints include rate limit headers (`X-RateLimit-*`)
- **Correlation IDs**: All requests require `X-Correlation-ID` header for distributed tracing
- **HMAC Validation**: All webhook endpoints require HMAC signature validation
- **Tenant Isolation**: All authenticated responses include `tenant_id` for data isolation

### Scope

This security policy applies to:
- OpenAPI 3.1.0 contract specifications
- Contract validation workflows
- Generated Pydantic models
- Documentation generated from contracts

### Out of Scope

The following are **not** covered by this security policy:
- Implementation code (backend services)
- Infrastructure configuration
- Third-party dependencies
- Issues in mock servers (Prism) - report to Prism maintainers

## Disclosure Policy

We follow responsible disclosure practices:

1. **Private Disclosure**: Vulnerabilities are reported privately
2. **Coordinated Release**: Security fixes are coordinated with affected parties
3. **Public Disclosure**: After fix is deployed, we may publish a security advisory
4. **Credit**: With your permission, we will credit you in security advisories

## Security Updates

Security updates are released as:
- **Patch versions** (1.0.x) for non-breaking security fixes
- **Minor versions** (1.x.0) for additive security enhancements
- **Major versions** (x.0.0) for breaking security changes (with migration guide)

See [CHANGELOG.md](CHANGELOG.md) for detailed security update history.

