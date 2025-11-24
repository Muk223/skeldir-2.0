-- ============================================================================
-- TEST: Channel State Transitions Audit Trigger
-- ============================================================================
-- Purpose: Validate that channel_taxonomy state changes produce audit records
-- Phase: 5 (Behavioral Verification)
-- Related: docs/database/CHANNEL_GOVERNANCE_AUDITABILITY_IMPLEMENTATION.md
--
-- Test Scenarios:
-- 1. Single transition (draft → active)
-- 2. Multiple transitions (draft → active → deprecated → archived)
-- 3. No-op update (state unchanged)
-- 4. Direct SQL bypass (still produces audit log)
-- ============================================================================

-- Setup: Create test channel
\echo 'SETUP: Creating test channel'
INSERT INTO channel_taxonomy (code, family, is_paid, display_name, state)
VALUES ('test_channel_audit', 'paid_social', true, 'Test Channel for Audit', 'draft')
ON CONFLICT (code) DO UPDATE SET state = 'draft';

-- Verify initial state
\echo 'VERIFY: Initial state is draft'
SELECT 
    CASE 
        WHEN state = 'draft' THEN '✅ PASS: Initial state is draft'
        ELSE '❌ FAIL: Initial state is not draft'
    END AS validation_status
FROM channel_taxonomy
WHERE code = 'test_channel_audit';

-- ============================================================================
-- Test Case 1: Single Transition (Happy Path)
-- ============================================================================

\echo ''
\echo 'TEST CASE 1: Single Transition (draft → active)'

-- Set session variables (simulating application layer)
SET LOCAL app.channel_state_change_by = 'test_admin@skeldir.com';
SET LOCAL app.channel_state_change_reason = 'Promoting test channel to production';

-- Record initial transition count
\echo 'BEFORE: Transition count'
SELECT COUNT(*) as transition_count_before
FROM channel_state_transitions
WHERE channel_code = 'test_channel_audit';

-- Execute state transition
UPDATE channel_taxonomy
SET state = 'active'
WHERE code = 'test_channel_audit';

-- Clear session variables
RESET app.channel_state_change_by;
RESET app.channel_state_change_reason;

-- Verify state changed
\echo 'VERIFY: State changed to active'
SELECT 
    CASE 
        WHEN state = 'active' THEN '✅ PASS: State changed to active'
        ELSE '❌ FAIL: State did not change to active'
    END AS validation_status
FROM channel_taxonomy
WHERE code = 'test_channel_audit';

-- Verify transition row created
\echo 'VERIFY: Transition row created'
SELECT 
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: Exactly one transition row created'
        ELSE '❌ FAIL: Expected 1 transition row, got ' || COUNT(*)::text
    END AS validation_status
FROM channel_state_transitions
WHERE channel_code = 'test_channel_audit';

-- Verify transition row content
\echo 'VERIFY: Transition row content'
SELECT 
    CASE 
        WHEN from_state = 'draft' AND to_state = 'active' 
             AND changed_by = 'test_admin@skeldir.com'
             AND reason = 'Promoting test channel to production'
        THEN '✅ PASS: Transition row has correct from_state, to_state, changed_by, and reason'
        ELSE '❌ FAIL: Transition row content incorrect'
    END AS validation_status
FROM channel_state_transitions
WHERE channel_code = 'test_channel_audit'
ORDER BY changed_at DESC
LIMIT 1;

-- ============================================================================
-- Test Case 2: Multiple Transitions (Lifecycle)
-- ============================================================================

\echo ''
\echo 'TEST CASE 2: Multiple Transitions (active → deprecated → archived)'

-- Transition 2: active → deprecated
SET LOCAL app.channel_state_change_by = 'product@skeldir.com';
SET LOCAL app.channel_state_change_reason = 'Low performance, consolidating channels';

UPDATE channel_taxonomy
SET state = 'deprecated'
WHERE code = 'test_channel_audit';

RESET app.channel_state_change_by;
RESET app.channel_state_change_reason;

-- Transition 3: deprecated → archived
SET LOCAL app.channel_state_change_by = 'admin@skeldir.com';
SET LOCAL app.channel_state_change_reason = 'Channel fully retired';

UPDATE channel_taxonomy
SET state = 'archived'
WHERE code = 'test_channel_audit';

RESET app.channel_state_change_by;
RESET app.channel_state_change_reason;

-- Verify final state
\echo 'VERIFY: Final state is archived'
SELECT 
    CASE 
        WHEN state = 'archived' THEN '✅ PASS: Final state is archived'
        ELSE '❌ FAIL: Final state is not archived'
    END AS validation_status
FROM channel_taxonomy
WHERE code = 'test_channel_audit';

-- Verify three transitions exist
\echo 'VERIFY: Three transitions exist'
SELECT 
    CASE 
        WHEN COUNT(*) = 3 THEN '✅ PASS: Exactly three transition rows exist'
        ELSE '❌ FAIL: Expected 3 transition rows, got ' || COUNT(*)::text
    END AS validation_status
FROM channel_state_transitions
WHERE channel_code = 'test_channel_audit';

-- Verify transition order
\echo 'VERIFY: Transition order'
SELECT 
    CASE 
        WHEN (SELECT from_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC LIMIT 1) = 'draft'
         AND (SELECT to_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC LIMIT 1) = 'active'
         AND (SELECT from_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC OFFSET 1 LIMIT 1) = 'active'
         AND (SELECT to_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC OFFSET 1 LIMIT 1) = 'deprecated'
         AND (SELECT from_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC OFFSET 2 LIMIT 1) = 'deprecated'
         AND (SELECT to_state FROM channel_state_transitions WHERE channel_code = 'test_channel_audit' ORDER BY changed_at ASC OFFSET 2 LIMIT 1) = 'archived'
        THEN '✅ PASS: Transitions are in correct order (draft→active→deprecated→archived)'
        ELSE '❌ FAIL: Transition order incorrect'
    END AS validation_status;

-- ============================================================================
-- Test Case 3: No-op Update (State Unchanged)
-- ============================================================================

\echo ''
\echo 'TEST CASE 3: No-op Update (State Unchanged)'

-- Record transition count before no-op update
SELECT COUNT(*) INTO TEMP TABLE transition_count_before_noop
FROM channel_state_transitions
WHERE channel_code = 'test_channel_audit';

-- Update display_name without changing state
UPDATE channel_taxonomy
SET display_name = 'Updated Display Name'
WHERE code = 'test_channel_audit'
  AND state = 'archived';  -- Ensure state doesn't change

-- Verify no new transition row created
\echo 'VERIFY: No new transition row on no-op update'
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM channel_state_transitions WHERE channel_code = 'test_channel_audit') = 
             (SELECT COUNT(*) FROM transition_count_before_noop)
        THEN '✅ PASS: No new transition row created on no-op update'
        ELSE '❌ FAIL: New transition row created on no-op update'
    END AS validation_status;

DROP TABLE transition_count_before_noop;

-- ============================================================================
-- Test Case 4: Direct SQL Bypass (Still Produces Audit Log)
-- ============================================================================

\echo ''
\echo 'TEST CASE 4: Direct SQL Bypass (Still Produces Audit Log)'

-- Create another test channel
INSERT INTO channel_taxonomy (code, family, is_paid, display_name, state)
VALUES ('test_channel_bypass', 'paid_social', true, 'Test Channel for Bypass', 'active')
ON CONFLICT (code) DO UPDATE SET state = 'active';

-- Record transition count before bypass
SELECT COUNT(*) INTO TEMP TABLE transition_count_before_bypass
FROM channel_state_transitions
WHERE channel_code = 'test_channel_bypass';

-- Direct SQL update (bypassing application layer, no session variables set)
UPDATE channel_taxonomy
SET state = 'deprecated'
WHERE code = 'test_channel_bypass';

-- Verify transition row still created (trigger guarantee)
\echo 'VERIFY: Transition row created even for direct SQL bypass'
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM channel_state_transitions WHERE channel_code = 'test_channel_bypass') > 
             (SELECT COUNT(*) FROM transition_count_before_bypass)
        THEN '✅ PASS: Transition row created even for direct SQL bypass'
        ELSE '❌ FAIL: No transition row created for direct SQL bypass'
    END AS validation_status;

-- Verify changed_by falls back to 'system' when session variable unset
\echo 'VERIFY: changed_by falls back to system for bypass'
SELECT 
    CASE 
        WHEN changed_by = 'system' THEN '✅ PASS: changed_by falls back to system for bypass'
        ELSE '❌ FAIL: changed_by is not system for bypass'
    END AS validation_status
FROM channel_state_transitions
WHERE channel_code = 'test_channel_bypass'
ORDER BY changed_at DESC
LIMIT 1;

DROP TABLE transition_count_before_bypass;

-- ============================================================================
-- Cleanup
-- ============================================================================

\echo ''
\echo 'CLEANUP: Removing test channels'

-- Delete test channels (CASCADE will delete transition records)
DELETE FROM channel_taxonomy
WHERE code IN ('test_channel_audit', 'test_channel_bypass');

\echo '✅ All tests complete'




