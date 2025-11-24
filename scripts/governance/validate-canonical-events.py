#!/usr/bin/env python3
"""
Skeldir Canonical Event Taxonomy Validator
Validates canonical events and state machine against ledger schema.

Exit Gates:
- C0.2: State Machine Completeness - Every ledger state has canonical event
- C0.3: Transition Uniqueness - No duplicate state transitions

Exit code 0: All validations pass
Exit code 1: Validation failures found
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import yaml

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def load_yaml(file_path: Path) -> Dict:
    """Load YAML file and return parsed content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}Error loading {file_path}: {e}{NC}")
        sys.exit(1)


def validate_category_completeness(canonical_events: Dict, business_categories: Dict) -> Tuple[bool, List[str]]:
    """
    Gate C0.1: Verify all four business categories have at least one canonical event.
    """
    violations = []
    
    required_categories = ["payment_capture", "refund", "order_state_change", "revenue_state_transition"]
    
    for category in required_categories:
        # Find canonical events for this category
        events_in_category = [
            event_name for event_name, event_data in canonical_events.items()
            if event_data.get("category") == category
        ]
        
        if not events_in_category:
            violations.append(
                f"{RED}X{NC} Category '{category}': No canonical events found"
            )
        else:
            print(f"{GREEN}OK{NC} Category '{category}': {len(events_in_category)} event(s) - {', '.join(events_in_category)}")
    
    return len(violations) == 0, violations


def validate_state_machine_completeness(
    canonical_events: Dict,
    state_machine: Dict,
    ledger_states: List[str]
) -> Tuple[bool, List[str]]:
    """
    Gate C0.2: Verify every ledger state has at least one canonical event that transitions to it.
    """
    violations = []
    
    # Collect all 'to' states from canonical events
    states_with_transitions = set()
    
    for event_name, event_data in canonical_events.items():
        ledger_impact = event_data.get("ledger_impact", {})
        state_transition = ledger_impact.get("state_transition", {})
        to_state = state_transition.get("to")
        
        if to_state:
            states_with_transitions.add(to_state)
    
    # Check each required ledger state
    for state in ledger_states:
        if state not in states_with_transitions:
            violations.append(
                f"{RED}X{NC} Ledger state '{state}': No canonical event transitions to this state"
            )
        else:
            # Find which events transition to this state
            events = [
                name for name, data in canonical_events.items()
                if data.get("ledger_impact", {}).get("state_transition", {}).get("to") == state
            ]
            print(f"{GREEN}OK{NC} Ledger state '{state}': Covered by {', '.join(events)}")
    
    return len(violations) == 0, violations


def validate_transition_uniqueness(canonical_events: Dict) -> Tuple[bool, List[str]]:
    """
    Gate C0.3: Verify no two canonical events have identical (from_state, to_state) transitions.
    """
    violations = []
    
    # Track transitions and which events define them
    transition_map: Dict[Tuple, List[str]] = {}
    
    for event_name, event_data in canonical_events.items():
        ledger_impact = event_data.get("ledger_impact", {})
        state_transition = ledger_impact.get("state_transition", {})
        
        from_state = state_transition.get("from")
        to_state = state_transition.get("to")
        
        if to_state:  # Only check if transition is defined
            transition_key = (from_state, to_state)
            
            if transition_key not in transition_map:
                transition_map[transition_key] = []
            transition_map[transition_key].append(event_name)
    
    # Find duplicates
    for transition, events in transition_map.items():
        if len(events) > 1:
            from_state, to_state = transition
            from_str = from_state if from_state else "null"
            violations.append(
                f"{RED}X{NC} Duplicate transition ({from_str} -> {to_state}): {', '.join(events)}"
            )
        else:
            from_state, to_state = transition
            from_str = from_state if from_state else "null"
            print(f"{GREEN}OK{NC} Unique transition ({from_str} -> {to_state}): {events[0]}")
    
    return len(violations) == 0, violations


def validate_state_machine_consistency(
    state_machine: Dict,
    canonical_events: Dict
) -> Tuple[bool, List[str]]:
    """
    Verify state machine transitions are consistent with canonical events.
    """
    violations = []
    
    defined_transitions = state_machine.get("transitions", [])
    
    for transition in defined_transitions:
        from_state = transition.get("from")
        to_state = transition.get("to")
        triggered_by = transition.get("triggered_by", [])
        required = transition.get("required", False)
        
        # Verify triggered_by events exist
        for event_name in triggered_by:
            if event_name not in canonical_events:
                violations.append(
                    f"{RED}✗{NC} Transition ({from_state} → {to_state}): References unknown event '{event_name}'"
                )
            else:
                # Verify event actually defines this transition
                event = canonical_events[event_name]
                event_transition = event.get("ledger_impact", {}).get("state_transition", {})
                event_from = event_transition.get("from")
                event_to = event_transition.get("to")
                
                if event_from != from_state or event_to != to_state:
                    violations.append(
                        f"{RED}X{NC} Event '{event_name}': Defines ({event_from} -> {event_to}), "
                        f"but state machine says it triggers ({from_state} -> {to_state})"
                    )
    
    if not violations:
        print(f"{GREEN}OK{NC} State machine transitions consistent with canonical events")
    
    return len(violations) == 0, violations


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate canonical event taxonomy and state machine'
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    args = parser.parse_args()
    
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Skeldir Canonical Events Validation{NC}")
    print(f"{BLUE}========================================{NC}")
    print()
    
    # Load canonical events
    canonical_events_path = repo_root / 'api-contracts' / 'governance' / 'canonical-events.yaml'
    
    if not canonical_events_path.exists():
        print(f"{RED}X Canonical events file not found: {canonical_events_path}{NC}")
        sys.exit(1)
    
    canonical_data = load_yaml(canonical_events_path)
    
    canonical_events = canonical_data.get('canonical_events', {})
    business_categories = canonical_data.get('business_event_categories', {})
    state_machine = canonical_data.get('revenue_state_machine', {})
    
    # Expected ledger states from schema
    ledger_states = ["authorized", "captured", "refunded", "chargeback"]
    
    # Run validations
    all_violations = []
    all_passed = True
    
    # Gate C0.1: Category Completeness
    print(f"{BLUE}Gate C0.1: Category Completeness{NC}")
    print("-" * 60)
    success, violations = validate_category_completeness(canonical_events, business_categories)
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Gate C0.2: State Machine Completeness
    print(f"{BLUE}Gate C0.2: State Machine Completeness{NC}")
    print("-" * 60)
    success, violations = validate_state_machine_completeness(canonical_events, state_machine, ledger_states)
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Gate C0.3: Transition Uniqueness
    print(f"{BLUE}Gate C0.3: Transition Uniqueness{NC}")
    print("-" * 60)
    success, violations = validate_transition_uniqueness(canonical_events)
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Additional: State Machine Consistency
    print(f"{BLUE}Additional: State Machine Consistency{NC}")
    print("-" * 60)
    success, violations = validate_state_machine_consistency(state_machine, canonical_events)
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Summary
    print(f"{BLUE}========================================{NC}")
    if all_passed:
        print(f"{GREEN}OK ALL VALIDATIONS PASSED{NC}")
        print(f"{GREEN}========================================{NC}")
        print()
        print(f"{GREEN}Canonical Events: {len(canonical_events)}{NC}")
        print(f"{GREEN}Ledger States Covered: {len(ledger_states)}/{len(ledger_states)}{NC}")
        print(f"{GREEN}Exit Gates: C0.1 OK, C0.2 OK, C0.3 OK{NC}")
        print()
        sys.exit(0)
    else:
        print(f"{RED}X VALIDATION FAILED{NC}")
        print(f"{RED}========================================{NC}")
        print()
        print(f"{RED}Violations Found:{NC}")
        for violation in all_violations:
            print(f"  {violation}")
        print()
        print(f"{YELLOW}Action Required:{NC}")
        print(f"  1. Review canonical-events.yaml for completeness")
        print(f"  2. Ensure all ledger states have canonical events")
        print(f"  3. Remove duplicate state transitions")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()

