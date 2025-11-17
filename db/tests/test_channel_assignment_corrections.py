-- ============================================================================
-- TEST: Channel Assignment Corrections Audit Trigger
-- ============================================================================
-- Purpose: Validate that attribution_allocations channel_code changes produce audit records
-- Phase: 5 (Behavioral Verification)
-- Related: docs/database/CHANNEL_GOVERNANCE_AUDITABILITY_IMPLEMENTATION.md
--
-- Test Scenarios:
-- 1. Single correction (google_search_paid → google_display_paid)
-- 2. Multiple corrections (same allocation corrected twice)
-- 3. No-op update (channel_code unchanged)
-- 4. Initial assignment (INSERT does NOT produce correction)
-- ============================================================================

-- Setup: Create test tenant and allocation
\echo 'SETUP: Creating test tenant'
INSERT INTO tenants (id, name, api_key_hash, notification_email)
VALUES ('10000000-0000-0000-0000-000000000001', 'Test Tenant', 'test_hash', 'test@example.com')
ON CONFLICT (id) DO NOTHING;

-- Setup: Ensure test channels exist and are active
\echo 'SETUP: Ensuring test channels exist'
INSERT INTO channel_taxonomy (code, family, is_paid, display_name, state)
VALUES 
    ('google_search_paid', 'paid_search', true, 'Google Search Paid', 'active'),
    ('google_display_paid', 'paid_search', true, 'Google Display Paid', 'active'),
    ('facebook_paid', 'paid_social', true, 'Facebook Paid', 'active')
ON CONFLICT (code) DO UPDATE SET state = 'active';

-- Setup: Create test allocation
\echo 'SETUP: Creating test allocation'
INSERT INTO attribution_allocations (
    id,
    tenant_id,
    channel_code,
    allocated_revenue_cents,
    confidence_score,
    allocation_date
)
VALUES (
    '20000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'google_search_paid',
    10000,
    0.95,
    CURRENT_DATE
)
ON CONFLICT (id) DO UPDATE SET channel_code = 'google_search_paid';

-- Verify initial state
\echo 'VERIFY: Initial channel_code is google_search_paid'
SELECT 
    CASE 
        WHEN channel_code = 'google_search_paid' THEN '✅ PASS: Initial channel_code is google_search_paid'
        ELSE '❌ FAIL: Initial channel_code is not google_search_paid'
    END AS validation_status
FROM attribution_allocations
WHERE id = '20000000-0000-0000-0000-000000000001';

-- ============================================================================
-- Test Case 1: Single Correction (Happy Path)
-- ============================================================================

\echo ''
\echo 'TEST CASE 1: Single Correction (google_search_paid → google_display_paid)'

-- Verify no corrections exist before
\echo 'BEFORE: Correction count'
SELECT COUNT(*) as correction_count_before
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001';

-- Set session variables (simulating application layer)
SET LOCAL app.current_tenant_id = '10000000-0000-0000-0000-000000000001';
SET LOCAL app.correction_by = 'support@skeldir.com';
SET LOCAL app.correction_reason = 'Campaign metadata indicates display network, not search';

-- Execute correction
UPDATE attribution_allocations
SET channel_code = 'google_display_paid'
WHERE id = '20000000-0000-0000-0000-000000000001';

-- Clear session variables
RESET app.current_tenant_id;
RESET app.correction_by;
RESET app.correction_reason;

-- Verify channel_code changed
\echo 'VERIFY: Channel_code changed to google_display_paid'
SELECT 
    CASE 
        WHEN channel_code = 'google_display_paid' THEN '✅ PASS: Channel_code changed to google_display_paid'
        ELSE '❌ FAIL: Channel_code did not change'
    END AS validation_status
FROM attribution_allocations
WHERE id = '20000000-0000-0000-0000-000000000001';

-- Verify correction row created
\echo 'VERIFY: Correction row created'
SELECT 
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: Exactly one correction row created'
        ELSE '❌ FAIL: Expected 1 correction row, got ' || COUNT(*)::text
    END AS validation_status
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001';

-- Verify correction row content
\echo 'VERIFY: Correction row content'
SELECT 
    CASE 
        WHEN entity_type = 'allocation'
         AND from_channel = 'google_search_paid'
         AND to_channel = 'google_display_paid'
         AND corrected_by = 'support@skeldir.com'
         AND reason = 'Campaign metadata indicates display network, not search'
        THEN '✅ PASS: Correction row has correct entity_type, from_channel, to_channel, corrected_by, and reason'
        ELSE '❌ FAIL: Correction row content incorrect'
    END AS validation_status
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001'
ORDER BY corrected_at DESC
LIMIT 1;

-- ============================================================================
-- Test Case 2: Multiple Corrections (Correction History)
-- ============================================================================

\echo ''
\echo 'TEST CASE 2: Multiple Corrections (google_display_paid → facebook_paid)'

-- Record correction count before second correction
SELECT COUNT(*) INTO TEMP TABLE correction_count_before_second
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001';

-- Second correction
SET LOCAL app.current_tenant_id = '10000000-0000-0000-0000-000000000001';
SET LOCAL app.correction_by = 'reconciliation@skeldir.com';
SET LOCAL app.correction_reason = 'Reconciliation identified correct channel as facebook_paid';

UPDATE attribution_allocations
SET channel_code = 'facebook_paid'
WHERE id = '20000000-0000-0000-0000-000000000001';

RESET app.current_tenant_id;
RESET app.correction_by;
RESET app.correction_reason;

-- Verify two corrections exist
\echo 'VERIFY: Two corrections exist'
SELECT 
    CASE 
        WHEN COUNT(*) = 2 THEN '✅ PASS: Exactly two correction rows exist'
        ELSE '❌ FAIL: Expected 2 correction rows, got ' || COUNT(*)::text
    END AS validation_status
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001';

-- Verify correction order
\echo 'VERIFY: Correction order'
SELECT 
    CASE 
        WHEN (SELECT from_channel FROM channel_assignment_corrections WHERE entity_id = '20000000-0000-0000-0000-000000000001' ORDER BY corrected_at ASC LIMIT 1) = 'google_search_paid'
         AND (SELECT to_channel FROM channel_assignment_corrections WHERE entity_id = '20000000-0000-0000-0000-000000000001' ORDER BY corrected_at ASC LIMIT 1) = 'google_display_paid'
         AND (SELECT from_channel FROM channel_assignment_corrections WHERE entity_id = '20000000-0000-0000-0000-000000000001' ORDER BY corrected_at ASC OFFSET 1 LIMIT 1) = 'google_display_paid'
         AND (SELECT to_channel FROM channel_assignment_corrections WHERE entity_id = '20000000-0000-0000-0000-000000000001' ORDER BY corrected_at ASC OFFSET 1 LIMIT 1) = 'facebook_paid'
        THEN '✅ PASS: Corrections are in correct order'
        ELSE '❌ FAIL: Correction order incorrect'
    END AS validation_status;

DROP TABLE correction_count_before_second;

-- ============================================================================
-- Test Case 3: No-op Update (Channel Unchanged)
-- ============================================================================

\echo ''
\echo 'TEST CASE 3: No-op Update (Channel Unchanged)'

-- Record correction count before no-op update
SELECT COUNT(*) INTO TEMP TABLE correction_count_before_noop
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000001';

-- Update allocated_revenue_cents without changing channel_code
UPDATE attribution_allocations
SET allocated_revenue_cents = 20000
WHERE id = '20000000-0000-0000-0000-000000000001'
  AND channel_code = 'facebook_paid';  -- Ensure channel_code doesn't change

-- Verify no new correction row created
\echo 'VERIFY: No new correction row on no-op update'
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM channel_assignment_corrections WHERE entity_id = '20000000-0000-0000-0000-000000000001') = 
             (SELECT COUNT(*) FROM correction_count_before_noop)
        THEN '✅ PASS: No new correction row created on no-op update'
        ELSE '❌ FAIL: New correction row created on no-op update'
    END AS validation_status;

DROP TABLE correction_count_before_noop;

-- ============================================================================
-- Test Case 4: Initial Assignment (INSERT Does NOT Produce Correction)
-- ============================================================================

\echo ''
\echo 'TEST CASE 4: Initial Assignment (INSERT Does NOT Produce Correction)'

-- Create new allocation via INSERT
INSERT INTO attribution_allocations (
    id,
    tenant_id,
    channel_code,
    allocated_revenue_cents,
    confidence_score,
    allocation_date
)
VALUES (
    '20000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'google_search_paid',
    5000,
    0.90,
    CURRENT_DATE
)
ON CONFLICT (id) DO NOTHING;

-- Verify no correction row created for INSERT
\echo 'VERIFY: No correction row created for initial INSERT'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: No correction row created for initial INSERT'
        ELSE '❌ FAIL: Correction row created for initial INSERT (should not happen)'
    END AS validation_status
FROM channel_assignment_corrections
WHERE entity_id = '20000000-0000-0000-0000-000000000002';

-- ============================================================================
-- Cleanup
-- ============================================================================

\echo ''
\echo 'CLEANUP: Removing test data'

-- Delete test allocations (CASCADE will delete correction records)
DELETE FROM attribution_allocations
WHERE id IN ('20000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002');

-- Delete test tenant (CASCADE will delete any remaining allocations)
DELETE FROM tenants
WHERE id = '10000000-0000-0000-0000-000000000001';

\echo '✅ All tests complete'

