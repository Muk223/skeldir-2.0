# Governance Negative Testing Procedures

**Purpose**: Validate that governance CI checks correctly detect and block intentional violations.

**Version**: 1.0  
**Author**: API Governance Lead  
**Date**: 2024-01-15

---

## Overview

Negative testing ("red team" testing) validates that governance enforcement mechanisms work by intentionally introducing violations and confirming they are detected. These tests must be performed before declaring governance operational.

---

## Test Suite 1: Ownership Metadata Validation

### Test 1.1: Missing x-domain
**Objective**: Verify Spectral catches missing `x-domain` metadata

**Procedure**:
1. Create test branch `test/neg-missing-x-domain`
2. Edit `api-contracts/openapi/v1/auth.yaml`
3. Remove `x-domain: "auth"` from info section
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"info must include x-domain extension to identify the business domain"`

**Cleanup**: Delete test branch

### Test 1.2: Missing x-owner
**Objective**: Verify Spectral catches missing `x-owner` metadata

**Procedure**:
1. Create test branch `test/neg-missing-x-owner`
2. Edit `api-contracts/openapi/v1/attribution.yaml`
3. Remove `x-owner: "attribution-owner@skeldir.com"` from info section
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"info must include x-owner extension to identify the domain owner"`

**Cleanup**: Delete test branch

### Test 1.3: Invalid x-owner format
**Objective**: Verify Spectral validates email format for x-owner

**Procedure**:
1. Create test branch `test/neg-invalid-owner-email`
2. Edit `api-contracts/openapi/v1/export.yaml`
3. Change `x-owner` to invalid format: `x-owner: "not-an-email"`
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"x-owner must be a valid email address (e.g., owner@skeldir.com)"`

**Cleanup**: Delete test branch

---

## Test Suite 2: Invariant Enforcement

### Test 2.1: Unconstrained currency field
**Objective**: Verify Spectral catches currency fields without pattern constraint

**Procedure**:
1. Create test branch `test/neg-unconstrained-currency`
2. Edit `api-contracts/openapi/v1/webhooks/shopify.yaml`
3. In `ShopifyOrderCreateRequest` schema, modify currency field:
   ```yaml
   currency:
     type: string
     description: "Order currency code"
     # Remove any pattern constraint
   ```
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"currency must have a pattern constraint (ISO 4217: ^[A-Z]{3}$ or ^[a-z]{3}$ for Stripe)"`

**Cleanup**: Delete test branch

### Test 2.2: Negative monetary value
**Objective**: Verify Spectral catches missing minimum constraint on revenue fields

**Procedure**:
1. Create test branch `test/neg-negative-revenue`
2. Edit `api-contracts/openapi/v1/attribution.yaml`
3. In `RealtimeRevenueResponse` schema, modify total_revenue:
   ```yaml
   total_revenue:
     type: number
     format: double
     # Remove minimum: 0 constraint
     description: Total revenue in dollars
   ```
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"total_revenue must have minimum: 0 constraint (monetary values cannot be negative)"`

**Cleanup**: Delete test branch

### Test 2.3: Loose string without constraints
**Objective**: Verify Spectral warns about unconstrained string fields

**Procedure**:
1. Create test branch `test/neg-loose-string`
2. Edit `api-contracts/openapi/v1/reconciliation.yaml`
3. Add a new string field without constraints:
   ```yaml
   arbitrary_field:
     type: string
     description: "Some field"
     # No format, pattern, enum, or maxLength
   ```
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI warns (severity: warn):  
`"arbitrary_field of type string should have format, pattern, enum, or maxLength to prevent unconstrained data"`

**Cleanup**: Delete test branch

---

## Test Suite 3: Coverage Validation

### Test 3.1: Implemented requirement with missing operation
**Objective**: Verify coverage validator catches status='implemented' but operation missing

**Procedure**:
1. Create test branch `test/neg-fake-implemented`
2. Edit `api-contracts/governance/coverage-manifest.yaml`
3. Add fake requirement:
   ```yaml
   - requirement_id: "FRQ-TEST-999"
     description: "Fake implemented requirement"
     operation_id: "nonExistentOperation"
     status: "implemented"
     priority: "critical"
   ```
4. Commit and push
5. Observe CI `validate-governance` job

**Expected Result**: CI fails with error message:  
`"FRQ-TEST-999 (critical): Status is 'implemented' but operation 'nonExistentOperation' NOT FOUND in contracts"`

**Cleanup**: Delete test branch

### Test 3.2: Missing critical requirement
**Objective**: Verify coverage validator warns about critical missing requirements

**Procedure**:
1. Review current coverage manifest
2. Confirm critical requirements marked as "missing" trigger warnings
3. Check CI output for existing critical gaps (Shopify order paid, Stripe refunds, etc.)

**Expected Result**: CI passes validation but includes warnings:  
`"⚠ Warning: X critical requirements marked as missing"`

**Cleanup**: No cleanup needed (documentation review only)

---

## Test Suite 4: Rate Limit Header Enforcement

### Test 4.1: Missing rate limit headers in 429 response
**Objective**: Verify Spectral catches 429 responses without required headers

**Procedure**:
1. Create test branch `test/neg-missing-rate-limit-headers`
2. Edit `api-contracts/openapi/v1/_common/components.yaml`
3. In `TooManyRequests` response, remove one or more rate limit headers:
   ```yaml
   headers:
     X-Correlation-ID:
       $ref: '#/components/headers/X-Correlation-ID'
     # Remove X-RateLimit-* headers
   ```
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"429 responses must include X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers"`

**Cleanup**: Delete test branch

---

## Test Suite 5: Operational Policy Enforcement

### Test 5.1: Missing operationId
**Objective**: Verify Spectral catches endpoints without operationId

**Procedure**:
1. Create test branch `test/neg-missing-operation-id`
2. Edit `api-contracts/openapi/v1/health.yaml`
3. Remove `operationId: healthCheck`
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"/api/health.get must have an operationId for code generation and coverage tracking"`

**Cleanup**: Delete test branch

### Test 5.2: Missing security definition
**Objective**: Verify Spectral catches operations without explicit security

**Procedure**:
1. Create test branch `test/neg-missing-security`
2. Edit `api-contracts/openapi/v1/attribution.yaml`
3. Remove `security:` field from an endpoint
4. Commit and push
5. Observe CI `lint-contracts` job

**Expected Result**: CI fails with error message:  
`"/api/attribution/revenue/realtime.get must explicitly define security (use empty array [] for public endpoints)"`

**Cleanup**: Delete test branch

---

## Test Execution Checklist

Before declaring governance operational, execute all tests and confirm:

- [ ] Test 1.1: Missing x-domain detected
- [ ] Test 1.2: Missing x-owner detected
- [ ] Test 1.3: Invalid x-owner format detected
- [ ] Test 2.1: Unconstrained currency detected
- [ ] Test 2.2: Negative monetary value detected
- [ ] Test 2.3: Loose string warning issued
- [ ] Test 3.1: Fake implemented requirement detected
- [ ] Test 3.2: Critical missing requirements warned
- [ ] Test 4.1: Missing rate limit headers detected
- [ ] Test 5.1: Missing operationId detected
- [ ] Test 5.2: Missing security definition detected

---

## Automation

### Future Enhancement: Automated Negative Testing

Create `scripts/governance/run-negative-tests.sh` that:
1. Iterates through all test scenarios
2. Creates temporary branches
3. Introduces violations
4. Triggers CI
5. Validates expected failures
6. Cleans up branches
7. Reports results

**Status**: Documented for manual execution in Phase G3  
**Future**: Automate in Phase G5 negative-test-suite.sh

---

## Validation Evidence

After completing all negative tests, document results in:
- `api-contracts/GOVERNANCE_AUDIT_REPORT.md`
- Include CI job URLs showing detected violations
- Capture screenshots of error messages
- Confirm all intentional violations blocked by automated checks

---

**Note**: These tests validate the governance system itself, not the contracts. They prove that enforcement mechanisms work correctly before relying on them for ongoing development.



