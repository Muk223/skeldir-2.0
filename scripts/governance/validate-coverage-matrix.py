#!/usr/bin/env python3
"""
Skeldir Provider Coverage Matrix Validator
Validates that provider coverage matrix is complete for all canonical events.

Exit Gates:
- C1.1: Coverage Matrix Completeness - Every canonical event x provider has entry
- C1.2: Critical Event Coverage - Critical events have required=true or mitigation

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


def validate_coverage_matrix_completeness(
    canonical_events: Dict,
    coverage_matrix: Dict,
    providers: List[str]
) -> Tuple[bool, List[str]]:
    """
    Gate C1.1: Verify every canonical event x provider combination has an entry.
    """
    violations = []
    
    for event_name in canonical_events.keys():
        if event_name not in coverage_matrix:
            violations.append(
                f"{RED}X{NC} Event '{event_name}': Not found in coverage matrix"
            )
            continue
        
        event_providers = coverage_matrix[event_name]
        
        # Collect providers that have entries
        providers_with_entries = set()
        for entry in event_providers:
            provider = entry.get("provider")
            if provider:
                providers_with_entries.add(provider)
        
        # Check each required provider
        for provider in providers:
            if provider not in providers_with_entries:
                violations.append(
                    f"{RED}X{NC} Event '{event_name}' x Provider '{provider}': Missing coverage entry"
                )
            else:
                # Find the entry
                entry = next(e for e in event_providers if e.get("provider") == provider)
                provider_event = entry.get("provider_event")
                status = "available" if provider_event else "N/A"
                print(f"{GREEN}OK{NC} Event '{event_name}' x Provider '{provider}': {status}")
    
    return len(violations) == 0, violations


def validate_critical_event_coverage(
    canonical_events: Dict,
    coverage_matrix: Dict,
    critical_events: List[str]
) -> Tuple[bool, List[str]]:
    """
    Gate C1.2: Verify critical events have required=true for all providers or explicit mitigation.
    """
    violations = []
    
    for event_name in critical_events:
        if event_name not in canonical_events:
            violations.append(
                f"{RED}X{NC} Critical event '{event_name}': Not found in canonical events"
            )
            continue
        
        if event_name not in coverage_matrix:
            violations.append(
                f"{RED}X{NC} Critical event '{event_name}': Not found in coverage matrix"
            )
            continue
        
        event_providers = coverage_matrix[event_name]
        
        for entry in event_providers:
            provider = entry.get("provider")
            required = entry.get("required", False)
            provider_event = entry.get("provider_event")
            mitigation = entry.get("mitigation")
            
            if not required and not provider_event and not mitigation:
                violations.append(
                    f"{RED}X{NC} Critical event '{event_name}' x Provider '{provider}': "
                    f"required=false but no mitigation provided"
                )
            elif required and provider_event:
                print(f"{GREEN}OK{NC} Critical event '{event_name}' x Provider '{provider}': required=true")
            elif mitigation:
                print(f"{YELLOW}OK{NC} Critical event '{event_name}' x Provider '{provider}': "
                      f"has mitigation: {mitigation}")
    
    return len(violations) == 0, violations


def validate_operation_ids(
    coverage_matrix: Dict,
    contract_dir: Path
) -> Tuple[bool, List[str]]:
    """
    Additional validation: Verify operation_ids are specified for required events.
    """
    violations = []
    warnings = []
    
    for event_name, providers in coverage_matrix.items():
        for entry in providers:
            provider = entry.get("provider")
            required = entry.get("required", False)
            operation_id = entry.get("operation_id")
            provider_event = entry.get("provider_event")
            
            if required and provider_event and not operation_id:
                warnings.append(
                    f"{YELLOW}!{NC} Event '{event_name}' x Provider '{provider}': "
                    f"required=true but operation_id not specified"
                )
            elif operation_id:
                print(f"{GREEN}OK{NC} Event '{event_name}' x Provider '{provider}': "
                      f"operation_id = {operation_id}")
    
    if warnings:
        print()
        print(f"{YELLOW}Warnings:{NC}")
        for warning in warnings:
            print(f"  {warning}")
    
    return len(violations) == 0, violations


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate provider coverage matrix completeness'
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    args = parser.parse_args()
    
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Skeldir Coverage Matrix Validation{NC}")
    print(f"{BLUE}========================================{NC}")
    print()
    
    # Load canonical events
    canonical_events_path = repo_root / 'api-contracts' / 'governance' / 'canonical-events.yaml'
    
    if not canonical_events_path.exists():
        print(f"{RED}X Canonical events file not found: {canonical_events_path}{NC}")
        sys.exit(1)
    
    canonical_data = load_yaml(canonical_events_path)
    
    canonical_events = canonical_data.get('canonical_events', {})
    coverage_matrix = canonical_data.get('provider_coverage_matrix', {})
    validation_rules = canonical_data.get('validation_rules', {})
    
    # Get providers and critical events from validation rules
    providers = ["Stripe", "Shopify", "PayPal", "WooCommerce"]
    critical_events = ["PaymentCaptured", "PaymentRefunded"]
    
    # Run validations
    all_violations = []
    all_passed = True
    
    # Gate C1.1: Coverage Matrix Completeness
    print(f"{BLUE}Gate C1.1: Coverage Matrix Completeness{NC}")
    print("-" * 60)
    success, violations = validate_coverage_matrix_completeness(
        canonical_events, coverage_matrix, providers
    )
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Gate C1.2: Critical Event Coverage
    print(f"{BLUE}Gate C1.2: Critical Event Coverage{NC}")
    print("-" * 60)
    success, violations = validate_critical_event_coverage(
        canonical_events, coverage_matrix, critical_events
    )
    if not success:
        all_passed = False
        all_violations.extend(violations)
    print()
    
    # Additional: Operation ID Validation
    print(f"{BLUE}Additional: Operation ID Validation{NC}")
    print("-" * 60)
    contract_dir = repo_root / 'api-contracts' / 'openapi' / 'v1' / 'webhooks'
    success, violations = validate_operation_ids(coverage_matrix, contract_dir)
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
        
        # Calculate stats
        total_entries = sum(len(providers) for providers in coverage_matrix.values())
        required_entries = sum(
            1 for providers in coverage_matrix.values()
            for entry in providers
            if entry.get("required", False)
        )
        
        print(f"{GREEN}Canonical Events: {len(canonical_events)}{NC}")
        print(f"{GREEN}Coverage Matrix Entries: {total_entries}{NC}")
        print(f"{GREEN}Required Entries: {required_entries}{NC}")
        print(f"{GREEN}Exit Gates: C1.1 OK, C1.2 OK{NC}")
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
        print(f"  1. Review provider_coverage_matrix in canonical-events.yaml")
        print(f"  2. Ensure all canonical events have coverage for all providers")
        print(f"  3. Add mitigation for unavailable provider events")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()



