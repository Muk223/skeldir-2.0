# Skeldir API Governance Charter

**Version:** 1.0  
**Status:** Active  
**Effective Date:** 2024-01-15  
**Last Updated:** 2024-01-15

---

## 1. Executive Summary

This charter establishes the constitutional framework for API governance at Skeldir Attribution Intelligence. It defines the "Rule of Law" for API contracts, ensuring they serve as the deterministic source of truth for all development activities. This document is binding and non-negotiable for all API-related changes.

**Core Mandate:** API contracts are not documentation—they are executable specifications that govern system behavior, policy enforcement, and audit trails.

---

## 2. Governance Principles

### 2.1 Source of Truth Hierarchy

API contracts (`api-contracts/openapi/v1/`) are the **sole authoritative source** for:

- Public request/response structure and data types
- Valid value ranges and format constraints for all public data
- Operational policies (rate limits, error semantics, idempotency requirements)
- Business invariants (currency formats, numeric ranges, timestamp formats)

**Non-Negotiable Rule:** No backend implementation, frontend integration, or infrastructure change may introduce semantics not explicitly reflected in the contracts.

### 2.2 Contract-First Development

All API changes **must** follow this sequence:

1. Business requirement documented
2. Contract updated and reviewed
3. Contract validation passes (structural + semantic + policy checks)
4. Models generated from contract
5. Implementation coded against generated models
6. Tests validate runtime behavior matches contract

**Violation:** Implementing endpoints before contract definition bypasses governance and is prohibited.

### 2.3 Semantic Completeness

Contracts must encode **behavioral semantics**, not just structural validity:

- **Structural:** "endpoint exists with request/response schemas" ✓
- **Semantic:** "currency field constrained to ISO 4217 uppercase pattern" ✓
- **Operational:** "429 responses include rate limit headers with reset timestamp" ✓

**Standard:** A contract passing OpenAPI validation but lacking invariants or policy metadata is **not** considered complete.

### 2.4 Policy Enforcement

Operational policies are **machine-verifiable** and **runtime-enforceable**:

- Rate limits encoded in contracts and validated by CI
- Error responses conform to RFC 7807 Problem schema
- Idempotency keys required for state-changing operations
- Deprecation follows 90-day notice window with sunset headers

**Enforcement:** CI pipeline gates merges on policy compliance. Manual overrides require explicit governance lead approval.

### 2.5 Traceability & Auditability

Every API behavior must be traceable:

- **Business Requirement** → **Invariant Registry** → **Contract Field** → **Generated Model** → **Runtime Behavior**

**Audit Standard:** An independent reviewer must be able to reconstruct the chain of authority for any field or endpoint using only repository artifacts.

---

## 3. Role Definitions & Authority

### 3.1 API Contract Owner (Primary Authority)

**Current Assignee:** TBD (api-governance-lead@skeldir.com)

**Responsibilities:**
- Final authority on contract integrity, coverage, and invariant completeness
- Reviews all contract changes for semantic correctness
- Maintains invariant and policy registries
- Absolute veto power over `api-contracts/` directory structure
- Custodian of governance charter and operational validation process

**Approval Required For:**
- All contract modifications
- Changes to governance registries (invariants, policies, coverage manifest)
- Updates to `.spectral.yaml` linting rules
- Breaking changes requiring major version bumps

### 3.2 Policy Steward

**Current Assignee:** TBD (policy-steward@skeldir.com)

**Responsibilities:**
- Defines and maintains operational policies (rate limits, idempotency, error model, deprecation)
- Reviews contract changes touching policy-sensitive areas
- Ensures policy metadata (`x-rate-limit`, `x-idempotency-key`) is correctly applied
- Tracks policy exceptions and time-bounded waivers

**Approval Required For:**
- Changes to rate limiting configuration
- Modifications to error response schemas
- Idempotency requirement changes
- Security scheme updates

### 3.3 Version Steward

**Current Assignee:** TBD (version-steward@skeldir.com)

**Responsibilities:**
- Enforces semantic versioning correctness (major.minor.patch)
- Classifies changes as breaking vs non-breaking
- Manages version baselines for breaking change detection
- Coordinates deprecation timelines and migration guides

**Approval Required For:**
- Version number increments
- Breaking change proposals
- Baseline updates (`api-contracts/baselines/`)
- Deprecation notices

### 3.4 CI Steward

**Current Assignee:** TBD (ci-steward@skeldir.com)

**Responsibilities:**
- Implements governance rules as automated CI checks
- Maintains contract validation workflow (`.github/workflows/contract-validation.yml`)
- Ensures CI checks are Replit-compatible
- Manages governance script maintenance (`scripts/governance/`)

**Approval Required For:**
- CI workflow modifications
- New governance check implementations
- Changes to validation script logic
- CI job dependency ordering

### 3.5 Domain Architects (Domain-Level Ownership)

Domain architects have authority over functional correctness within their business domain:

| Domain | Primary Owner | Business Stakeholder | Secondary Reviewer |
|--------|---------------|----------------------|--------------------|
| Authentication | TBD (auth-owner@skeldir.com) | Identity Team | API Contract Owner |
| Attribution | TBD (attribution-owner@skeldir.com) | Analytics Team | API Contract Owner |
| Reconciliation | TBD (reconciliation-owner@skeldir.com) | Finance Team | API Contract Owner |
| Export | TBD (export-owner@skeldir.com) | Data Team | API Contract Owner |
| Health | TBD (health-owner@skeldir.com) | Infrastructure Team | API Contract Owner |
| Webhooks (Shopify) | TBD (webhooks-owner@skeldir.com) | Integration Team | API Contract Owner |
| Webhooks (WooCommerce) | TBD (webhooks-owner@skeldir.com) | Integration Team | API Contract Owner |
| Webhooks (Stripe) | TBD (webhooks-owner@skeldir.com) | Integration Team | API Contract Owner |
| Webhooks (PayPal) | TBD (webhooks-owner@skeldir.com) | Integration Team | API Contract Owner |

**Domain Architect Responsibilities:**
- Validate contract changes reflect real business requirements
- Ensure domain-specific invariants are correctly applied
- Maintain domain coverage in coverage manifest
- Review contract changes for functional completeness

---

## 4. Artifact Hierarchy

### Level 0: Product Vision & Architecture (Conceptual Authority)

**Location:** `docs/architecture/`, product specifications

**Authority:** Defines business requirements and system constraints

**Governance:** Changes here drive updates to Level 1 artifacts

### Level 1: Contracts & Governance Registries (Canonical Source of Truth)

**Artifacts:**
- OpenAPI contracts (`api-contracts/openapi/v1/*.yaml`)
- Invariant registry (`api-contracts/governance/invariants.yaml`)
- Policy registry (`api-contracts/governance/policies.yaml`)
- Coverage manifest (`api-contracts/governance/coverage-manifest.yaml`)

**Authority:** These artifacts **define** what the system must do

**Governance:** All changes require role-based approval per Section 3

**Immutability:** Cannot be modified without governance review and CI validation

### Level 2: Generated Models & Derivative Artifacts (Strictly Downstream)

**Artifacts:**
- Pydantic models (`backend/app/schemas/*.py`)
- Mock server configurations (Prism endpoints)
- API documentation (Redoc/Swagger UI sites)
- Contract tests (Dredd/Pact when implemented)

**Authority:** Derived from Level 1—**no independent semantics allowed**

**Governance:** Generated via `scripts/generate-models.sh` and similar tooling

**Immutability:** Must be regenerated from contracts; manual edits prohibited

### Level 3: Runtime Telemetry & Evidence (Validation Authority)

**Artifacts:**
- Application logs with correlation IDs
- Error tracking (error_id → occurrence mapping)
- Rate limit metrics
- API usage analytics

**Authority:** Provides empirical evidence that runtime behavior matches contracts

**Governance:** Used for audits and policy refinement feedback loops

---

## 5. Review Protocols

### 5.1 Standard Contract Change Flow

1. **Proposal:** Developer creates feature branch with contract updates
2. **Self-Check:** Local validation passes (bundle, lint, generate models)
3. **PR Creation:** Automated CI runs structural + semantic + policy checks
4. **Domain Review:** Domain architect reviews for functional correctness
5. **Policy Review:** Policy steward reviews if rate limits/errors/idempotency affected
6. **Version Review:** Version steward reviews if version bump needed
7. **Governance Review:** API Contract Owner provides final approval
8. **Merge:** Only after all checks pass and all required reviews complete

### 5.2 Exception Handling

**Policy Exceptions** (e.g., temporarily higher rate limit for internal endpoints):

- Must be explicitly documented in contract via `x-exception` metadata
- Requires both Domain Architect and Policy Steward approval
- Must be time-bounded (expiration date in metadata)
- Tracked in quarterly governance audits

**Emergency Changes** (production incidents requiring immediate contract updates):

- API Contract Owner may approve without full review cycle
- Post-incident review required within 48 hours
- Retrospective must document lessons learned and governance gaps

### 5.3 Role-Specific Review Checklists

**API Contract Owner Checklist:**
- [ ] Change reflects documented business requirement
- [ ] All invariants from registry correctly applied
- [ ] Coverage manifest updated if new operations added
- [ ] Mappings to DB constraints and ledger are coherent
- [ ] Structural and semantic validity confirmed

**Policy Steward Checklist:**
- [ ] Rate limits consistent with policy registry
- [ ] Error responses use Problem schema
- [ ] Idempotency requirements clear and safe
- [ ] Security schemes appropriate for endpoint sensitivity
- [ ] No policy bypasses without documented exception

**Version Steward Checklist:**
- [ ] Change type matches version increment (major/minor/patch)
- [ ] Breaking changes appropriately classified
- [ ] Baseline comparison confirms breaking/non-breaking status
- [ ] Migration guide exists if breaking change
- [ ] Deprecation notice follows 90-day window if applicable

---

## 6. Governance Change Management

### 6.1 Charter Amendment Process

Changes to this charter require:

1. Proposal document with rationale and impact analysis
2. Review by all stewards (API Contract Owner, Policy, Version, CI)
3. Consensus approval (no objections from any steward)
4. 7-day comment period for stakeholder feedback
5. Update to charter with version increment and changelog

### 6.2 Registry Updates

**Invariant Registry Changes:**
- Proposed by Domain Architect or API Contract Owner
- Reviewed for consistency with existing invariants
- CI validators updated to enforce new invariants
- Existing contracts audited for compliance

**Policy Registry Changes:**
- Proposed by Policy Steward
- Impact assessment on all existing endpoints
- Phased rollout if affecting multiple contracts
- Metrics tracked to validate policy effectiveness

### 6.3 Quarterly Governance Audits

**Frequency:** Every 90 days

**Audit Scope:**
- Review all active policy exceptions (confirm still needed or expire)
- Spot-check random contracts for invariant compliance
- Validate domain owner assignments are current
- Review governance metrics (% of changes with violations caught by CI)
- Update charter if systemic issues identified

**Audit Owner:** API Contract Owner

**Audit Artifact:** Governance audit report published to `api-contracts/audits/`

---

## 7. Operational Metrics

### 7.1 Governance Effectiveness Metrics

**Metric 1: Contract Change Review Completeness**
- **Definition:** % of contract changes with all required role reviews completed before merge
- **Target:** 100%
- **Owner:** API Contract Owner

**Metric 2: CI Governance Check Failure Rate**
- **Definition:** % of CI runs where governance checks (linting, coverage, invariants) fail
- **Target:** Increasing failures = effective detection; decreasing = improving contract quality
- **Owner:** CI Steward

**Metric 3: Policy Compliance Time**
- **Definition:** Average time between policy change and full contract update
- **Target:** < 14 days
- **Owner:** Policy Steward

**Metric 4: Breaking Change Detection Accuracy**
- **Definition:** % of actual breaking changes correctly flagged by oasdiff
- **Target:** 100% (no false negatives)
- **Owner:** Version Steward

### 7.2 Reporting Cadence

- **Weekly:** CI failure rates shared with CI Steward
- **Monthly:** Review completeness reported to API Contract Owner
- **Quarterly:** All metrics presented in governance audit

---

## 8. System-Level Compliance Criteria

The governance system is considered **fully operational** when:

1. **100% Ownership Coverage:** All contracts have `x-owner` and `x-domain` metadata
2. **100% Invariant Compliance:** All invariant-linked fields satisfy registry constraints
3. **100% Policy Metadata:** All rate-limited endpoints have policy metadata and 429 semantics
4. **100% Coverage Mapping:** All operations from coverage manifest present in contracts
5. **100% Exit Gate Implementation:** All phase exit gates have corresponding CI checks
6. **Audit Trail Completeness:** Any field traceable from requirement → contract → runtime

**Validation:** Independent reviewer can navigate entire governance system using only repository documentation.

---

## 9. Escalation & Dispute Resolution

### 9.1 Technical Disputes

**Level 1:** Domain Architect and API Contract Owner discuss and resolve

**Level 2:** If unresolved, Policy Steward and Version Steward join for consensus

**Level 3:** If still unresolved, escalate to Engineering Director with written proposals from each party

### 9.2 Governance Process Disputes

**Resolution Authority:** API Contract Owner has final say on governance process interpretation

**Appeal Process:** Disputes may be appealed to quarterly governance audit for charter clarification

---

## 10. Amendment History

| Version | Date | Changes | Approvers |
|---------|------|---------|-----------|
| 1.0 | 2024-01-15 | Initial charter creation | API Contract Owner |

---

## 11. Acknowledgments

This charter synthesizes governance frameworks from:
- Jamie's Constitutional Governance Model (emphasis on operational semantics and traceability)
- Schmidt's Tactical Remediation Protocol (emphasis on machine-verifiable policy enforcement)

**Governing Philosophy:** Contracts govern behavior, not just describe structure. Governance without automation is aspiration; automation without governance is chaos.

---

**Document Owner:** API Contract Owner  
**Review Cycle:** Quarterly  
**Next Review Date:** 2024-04-15





