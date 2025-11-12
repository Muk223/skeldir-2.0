# Privacy Notes

## Privacy-First Architecture

Skeldir Attribution Intelligence is designed with **privacy by design** principles. These notes document the privacy constraints encoded in our API contracts and architectural assumptions.

## Core Privacy Principles

### 1. No Identity Resolution

**Mandate**: Eliminate all identity resolution, cross-device tracking, and PII storage.

- **No user identity resolution**: We do not attempt to match users across devices or sessions
- **No probabilistic matching**: No fingerprinting or probabilistic user identification
- **No cross-session tracking**: Each session is independent and ephemeral

### 2. Session-Scoped Data Only

**Constraint**: All event data is scoped to individual sessions with strict timeouts.

- **Session ID**: Ephemeral identifier valid for 30 minutes of inactivity
- **No persistence**: Session data is not persisted beyond the session timeout
- **No cross-session correlation**: Events from different sessions are never correlated

### 3. PII Stripping Requirements

**Mandate**: All webhook data must pass through PII stripping before persistence.

#### Required PII Stripping

All webhook endpoints (Shopify, WooCommerce, Stripe, PayPal) must:

1. **Strip email addresses**: Remove or hash all email fields before storage
2. **Strip IP addresses**: Remove IP addresses beyond rate limiting (memory-only)
3. **Strip names**: Remove or anonymize customer names
4. **Strip phone numbers**: Remove or hash phone number fields
5. **Strip addresses**: Remove or generalize physical addresses

#### Webhook Schema Requirements

Each webhook contract includes explicit privacy statements:

```yaml
description: |
  Webhook endpoint for [platform] order events.
  
  **Privacy Note**: This endpoint strips all PII (emails, IPs, names, addresses) 
  before persistence. Only session-scoped, anonymized event data is stored.
  No cross-session tracking or identity resolution is performed.
```

### 4. Tenant Isolation

**Assumption**: Tenant data isolation will be enforced at the database layer via PostgreSQL Row-Level Security (RLS).

- **Tenant ID**: All authenticated responses include `tenant_id` for data isolation
- **RLS Enforcement**: Database layer enforces tenant boundaries (not contract-level)
- **No Cross-Tenant Access**: Contracts assume RLS prevents cross-tenant data access

### 5. Rate Limiting and IP Handling

**Constraint**: IP addresses are used only for rate limiting and are not persisted.

- **Memory-only**: IP addresses stored in memory for rate limiting (not persisted)
- **No IP logging**: IP addresses are not logged or stored in database
- **Rate limit headers**: All responses include `X-RateLimit-*` headers

## Contract-Level Privacy Constraints

### Authentication Endpoints

- **No PII in responses**: Authentication responses do not expose email addresses or user identifiers
- **JWT tokens**: Tokens contain only non-PII claims (tenant_id, session_id, roles)
- **No user lookup**: Authentication does not expose user lookup capabilities

### Attribution Endpoints

- **Session-scoped**: All attribution data is scoped to individual sessions
- **No user tracking**: No user-level attribution or cross-session tracking
- **Anonymized data**: All attribution responses contain anonymized, session-scoped data

### Webhook Endpoints

All webhook contracts explicitly state:

1. **PII stripping**: Emails, IPs, names, addresses are stripped before persistence
2. **Session scoping**: Data is scoped to individual sessions (30-minute timeout)
3. **No identity resolution**: No cross-session or cross-device matching
4. **HMAC validation**: All webhooks require HMAC signature validation

### Export Endpoints

- **Tenant-scoped**: Exports are limited to authenticated tenant's data
- **No PII**: Exported data does not include PII fields
- **Session boundaries**: Exports respect session boundaries (no cross-session data)

## Implementation Assumptions

These privacy constraints are **architectural assumptions** encoded in contracts. Implementation must enforce:

1. **Database Layer**: PostgreSQL RLS enforces tenant isolation
2. **Application Layer**: PII stripping middleware processes all webhook data
3. **Session Management**: 30-minute inactivity timeout enforced
4. **Rate Limiting**: IP addresses used only for rate limiting (memory-only)

## Compliance

### GDPR Compliance

- **Right to erasure**: Session-scoped data automatically expires (30-minute timeout)
- **Data minimization**: Only necessary attribution data is collected
- **No profiling**: No user profiling or cross-session tracking

### CCPA Compliance

- **No sale of data**: No PII is collected or sold
- **Opt-out**: Not applicable (no PII collection)
- **Data deletion**: Automatic expiration via session timeout

## Future Considerations

These privacy constraints are **immutable** for v1.0 contracts. Future versions may:

- Add additional privacy controls (with major version bump)
- Enhance PII stripping requirements (additive changes only)
- Add privacy-related headers or metadata (additive changes only)

**Breaking changes** to privacy constraints require:
- Major version bump (v2.0.0)
- Migration guide
- 30-day notice period
- Stakeholder approval (compliance, legal, product)

## References

- [SECURITY.md](SECURITY.md): Security policy and vulnerability reporting
- [GOVERNANCE.md](docs/GOVERNANCE.md): Contract change process
- [CHANGELOG.md](CHANGELOG.md): Version history and privacy-related changes

