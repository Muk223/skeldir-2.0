#!/usr/bin/env python3
"""
Integration Mapping Validation Script (Phase C3)

Purpose: Validates integration mapping specifications for mechanical traceability

Exit Gates:
  C3.1 - Mapping Completeness: Every required provider event has complete field mappings
  C3.2 - Schema Consistency: All target columns exist in canonical schema, transforms valid
  C3.3 - State Transition Validity: All state transitions match canonical state machine

Exit Code: 0 if all gates pass, 1 if any validation fails
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ANSI colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Ensure UTF-8 encoding for output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Valid transform types
VALID_TRANSFORMS = {
    'as-is',
    'uppercase',
    'lowercase',
    'unix_to_timestamptz',
    'iso8601_to_timestamptz',
    'decimal_string_to_cents',
    'int_to_string',
    'prefix_provider',
    'constant'
}

# Expected ledger schema (simplified - in production, load from canonical_schema.yaml)
LEDGER_SCHEMA = {
    'revenue_ledger': {
        'transaction_id',
        'order_id',
        'amount_cents',
        'currency',
        'verification_timestamp',
        'verification_source',
        'state',
        'tenant_id',
        'created_at',
        'updated_at'
    },
    'revenue_state_transitions': {
        'id',
        'transaction_id',
        'from_state',
        'to_state',
        'transition_timestamp',
        'created_at'
    }
}

def load_yaml(file_path: Path) -> dict:
    """Load and parse YAML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}✗ ERROR: Failed to load {file_path}: {e}{RESET}")
        sys.exit(1)

def validate_c3_1_mapping_completeness(
    integration_maps: Dict[str, dict],
    coverage_matrix: List[dict]
) -> Tuple[bool, List[str]]:
    """
    Gate C3.1: Mapping Completeness
    
    Every required provider event from coverage matrix must have:
    - A mapping file
    - Field mappings for all critical ledger columns
    - Idempotency rules
    """
    print(f"\n{BLUE}Gate C3.1: Mapping Completeness{RESET}")
    
    errors = []
    passed = True
    
    # Critical ledger columns that MUST be mapped
    CRITICAL_COLUMNS = {
        'transaction_id',
        'amount_cents',
        'currency',
        'verification_timestamp',
        'verification_source'
    }
    
    # Build required events from coverage matrix
    # Structure: {canonical_event: [{provider, provider_event, required, ...}, ...]}
    required_events = {}
    for canonical_event, entries in coverage_matrix.items():
        if isinstance(entries, list):
            for entry in entries:
                if entry.get('required'):
                    provider = entry['provider']
                    event_name = entry['provider_event']
                    
                    if provider not in required_events:
                        required_events[provider] = []
                    required_events[provider].append(event_name)
    
    # Validate each required event has complete mapping
    for provider, events in required_events.items():
        provider_lower = provider.lower()
        
        if provider_lower not in integration_maps:
            errors.append(f"Missing integration map file for provider: {provider}")
            passed = False
            continue
        
        provider_map = integration_maps[provider_lower]
        mappings = provider_map.get('mappings', {})
        
        for event in events:
            if event not in mappings:
                errors.append(f"{provider}: Missing mapping for required event '{event}'")
                passed = False
                continue
            
            event_mapping = mappings[event]
            
            # Check critical fields are mapped
            mapped_columns = set()
            for field in event_mapping.get('fields', []):
                target_col = field.get('target_column')
                if target_col:
                    mapped_columns.add(target_col)
            
            missing_critical = CRITICAL_COLUMNS - mapped_columns
            if missing_critical:
                errors.append(
                    f"{provider}.{event}: Missing mappings for critical columns: {missing_critical}"
                )
                passed = False
            
            # Check idempotency rules exist
            if 'idempotency' not in event_mapping:
                errors.append(f"{provider}.{event}: Missing idempotency rules")
                passed = False
            else:
                idempotency = event_mapping['idempotency']
                if not idempotency.get('key_field') or not idempotency.get('duplicate_handling'):
                    errors.append(
                        f"{provider}.{event}: Incomplete idempotency specification"
                    )
                    passed = False
            
            # Check state transition exists (if event implies state change)
            canonical_event = event_mapping.get('canonical_event')
            if canonical_event in ['PaymentCaptured', 'PaymentRefunded', 'OrderCreated', 'PaymentDisputed']:
                if 'state_transition' not in event_mapping:
                    errors.append(f"{provider}.{event}: Missing state_transition for {canonical_event}")
                    passed = False
    
    # Print results
    if passed:
        print(f"  {GREEN}✓ OK All {sum(len(v) for v in required_events.values())} required events have complete mappings{RESET}")
    else:
        print(f"  {RED}✗ FAIL Mapping completeness issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def validate_c3_2_schema_consistency(
    integration_maps: Dict[str, dict]
) -> Tuple[bool, List[str]]:
    """
    Gate C3.2: Schema Consistency
    
    All field mappings must:
    - Target existing ledger columns
    - Use valid transform types
    - Have required fields marked as required=true
    """
    print(f"\n{BLUE}Gate C3.2: Schema Consistency{RESET}")
    
    errors = []
    passed = True
    
    for provider, provider_map in integration_maps.items():
        mappings = provider_map.get('mappings', {})
        
        for event_name, event_mapping in mappings.items():
            fields = event_mapping.get('fields', [])
            
            for field in fields:
                target_table = field.get('target_table')
                target_column = field.get('target_column')
                transform = field.get('transform')
                required = field.get('required', False)
                
                # Validate target table exists
                if target_table and target_table not in LEDGER_SCHEMA:
                    errors.append(
                        f"{provider}.{event_name}: Unknown target_table '{target_table}'"
                    )
                    passed = False
                
                # Validate target column exists in table
                if target_table and target_column:
                    if target_column not in LEDGER_SCHEMA.get(target_table, set()):
                        errors.append(
                            f"{provider}.{event_name}: Column '{target_column}' not in '{target_table}' schema"
                        )
                        passed = False
                
                # Validate transform type
                if transform and transform not in VALID_TRANSFORMS:
                    errors.append(
                        f"{provider}.{event_name}: Invalid transform '{transform}' for {target_column}"
                    )
                    passed = False
                
                # Validate required fields have required=true
                critical_columns = {'transaction_id', 'amount_cents', 'currency', 'verification_timestamp'}
                if target_column in critical_columns and not required:
                    errors.append(
                        f"{provider}.{event_name}: Critical field '{target_column}' should be required=true"
                    )
                    passed = False
                
                # Validate constant transform has constant_value
                if transform == 'constant' and 'constant_value' not in field:
                    errors.append(
                        f"{provider}.{event_name}: Transform 'constant' missing constant_value for {target_column}"
                    )
                    passed = False
                
                # Validate prefix_provider has prefix
                if transform == 'prefix_provider' and 'prefix' not in field:
                    errors.append(
                        f"{provider}.{event_name}: Transform 'prefix_provider' missing prefix for {target_column}"
                    )
                    passed = False
    
    if passed:
        print(f"  {GREEN}✓ OK All field mappings consistent with ledger schema{RESET}")
    else:
        print(f"  {RED}✗ FAIL Schema consistency issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def validate_c3_3_state_transition_validity(
    integration_maps: Dict[str, dict],
    canonical_events: dict
) -> Tuple[bool, List[str]]:
    """
    Gate C3.3: State Transition Validity
    
    All state transitions must:
    - Match canonical state machine transitions
    - Have valid from_state and to_state
    - Match the canonical event's implied transition
    """
    print(f"\n{BLUE}Gate C3.3: State Transition Validity{RESET}")
    
    errors = []
    passed = True
    
    # Build valid transitions from canonical events
    # States are list of dicts with 'name' keys
    valid_states = set()
    for state in canonical_events['revenue_state_machine']['states']:
        if isinstance(state, dict):
            valid_states.add(state['name'])
        else:
            valid_states.add(state)
    
    valid_transitions = {}
    
    for transition in canonical_events['revenue_state_machine']['transitions']:
        # Transitions have 'triggered_by' as a list of canonical events
        from_state = transition.get('from')
        to_state = transition['to']
        triggered_by = transition.get('triggered_by', [])
        
        for event_type in triggered_by:
            valid_transitions[event_type] = (from_state, to_state)
    
    # Validate each mapping's state transition
    for provider, provider_map in integration_maps.items():
        mappings = provider_map.get('mappings', {})
        
        for event_name, event_mapping in mappings.items():
            canonical_event = event_mapping.get('canonical_event')
            state_transition = event_mapping.get('state_transition')
            
            if not canonical_event:
                continue  # Skip if no canonical event mapping
            
            if not state_transition:
                errors.append(
                    f"{provider}.{event_name}: Canonical event '{canonical_event}' requires state_transition"
                )
                passed = False
                continue
            
            from_state = state_transition.get('from_state')
            to_state = state_transition.get('to_state')
            
            # Validate states are valid (null is valid for from_state in OrderCreated)
            if from_state and from_state not in valid_states:
                errors.append(
                    f"{provider}.{event_name}: Invalid from_state '{from_state}' (valid: {valid_states})"
                )
                passed = False
            
            if to_state not in valid_states:
                errors.append(
                    f"{provider}.{event_name}: Invalid to_state '{to_state}' (valid: {valid_states})"
                )
                passed = False
            
            # Validate transition matches canonical event
            if canonical_event in valid_transitions:
                expected_from, expected_to = valid_transitions[canonical_event]
                
                if from_state != expected_from or to_state != expected_to:
                    errors.append(
                        f"{provider}.{event_name}: State transition ({from_state} -> {to_state}) "
                        f"doesn't match canonical event '{canonical_event}' ({expected_from} -> {expected_to})"
                    )
                    passed = False
    
    if passed:
        print(f"  {GREEN}✓ OK All state transitions valid and match canonical state machine{RESET}")
    else:
        print(f"  {RED}✗ FAIL State transition issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def main():
    """Main validation orchestrator"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Integration Mapping Validation (Phase C3){RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Load canonical events (for state machine validation)
    canonical_events_path = project_root / 'api-contracts' / 'governance' / 'canonical-events.yaml'
    if not canonical_events_path.exists():
        print(f"{RED}✗ ERROR: canonical-events.yaml not found at {canonical_events_path}{RESET}")
        sys.exit(1)
    
    canonical_events = load_yaml(canonical_events_path)
    
    # Load integration mapping files
    integration_maps_dir = project_root / 'api-contracts' / 'governance' / 'integration-maps'
    if not integration_maps_dir.exists():
        print(f"{RED}✗ ERROR: integration-maps directory not found at {integration_maps_dir}{RESET}")
        sys.exit(1)
    
    integration_maps = {}
    for provider in ['stripe', 'shopify', 'paypal', 'woocommerce']:
        map_file = integration_maps_dir / f'{provider}.yaml'
        if map_file.exists():
            integration_maps[provider] = load_yaml(map_file)
            print(f"{GREEN}✓ Loaded {provider}.yaml{RESET}")
        else:
            print(f"{YELLOW}⚠ Warning: {provider}.yaml not found{RESET}")
    
    if not integration_maps:
        print(f"{RED}✗ ERROR: No integration mapping files found{RESET}")
        sys.exit(1)
    
    # Get coverage matrix for required events
    coverage_matrix = canonical_events.get('provider_coverage_matrix', [])
    
    # Run exit gate validations
    all_passed = True
    
    gate_c3_1_passed, _ = validate_c3_1_mapping_completeness(integration_maps, coverage_matrix)
    all_passed = all_passed and gate_c3_1_passed
    
    gate_c3_2_passed, _ = validate_c3_2_schema_consistency(integration_maps)
    all_passed = all_passed and gate_c3_2_passed
    
    gate_c3_3_passed, _ = validate_c3_3_state_transition_validity(integration_maps, canonical_events)
    all_passed = all_passed and gate_c3_3_passed
    
    # Print summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Exit Gate Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    gates = [
        ('C3.1', 'Mapping Completeness', gate_c3_1_passed),
        ('C3.2', 'Schema Consistency', gate_c3_2_passed),
        ('C3.3', 'State Transition Validity', gate_c3_3_passed)
    ]
    
    for gate_id, gate_name, passed in gates:
        status = f"{GREEN}OK{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {gate_id} ({gate_name}): {status}")
    
    gate_summary = ', '.join(f"{g[0]} {'OK' if g[2] else 'FAIL'}" for g in gates)
    print(f"\n{BLUE}Exit Gates: {gate_summary}{RESET}")
    
    if all_passed:
        print(f"\n{GREEN}✓ OK ALL VALIDATIONS PASSED{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}✗ FAIL Some validations failed - see errors above{RESET}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()

