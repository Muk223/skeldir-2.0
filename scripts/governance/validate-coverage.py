#!/usr/bin/env python3
"""
Skeldir API Coverage Validator
Validates that all business requirements in coverage manifest have corresponding operations in contracts.
Exit code 0: All validations pass
Exit code 1: Coverage violations found
"""

import sys
import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

def load_yaml(file_path: Path) -> Dict:
    """Load YAML file and return parsed content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}Error loading {file_path}: {e}{NC}")
        sys.exit(1)

def find_operation_ids_in_contract(contract_data: Dict) -> Set[str]:
    """Extract all operationId values from an OpenAPI contract."""
    operation_ids = set()
    
    paths = contract_data.get('paths', {})
    for path, path_item in paths.items():
        for method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
            if method in path_item:
                operation = path_item[method]
                if 'operationId' in operation:
                    operation_ids.add(operation['operationId'])
    
    return operation_ids

def validate_coverage(repo_root: Path, verbose: bool = False) -> Tuple[bool, List[str], Dict]:
    """
    Validate coverage manifest against bundled OpenAPI contracts.
    Returns (success, violations, statistics)
    """
    manifest_path = repo_root / 'api-contracts' / 'governance' / 'coverage-manifest.yaml'
    canonical_events_path = repo_root / 'api-contracts' / 'governance' / 'canonical-events.yaml'
    dist_dir = repo_root / 'api-contracts' / 'dist' / 'openapi' / 'v1'
    
    # Load coverage manifest
    if not manifest_path.exists():
        return False, [f"Coverage manifest not found: {manifest_path}"], {}
    
    manifest = load_yaml(manifest_path)
    
    # Load canonical events for validation (Phase C2 enhancement)
    canonical_events = {}
    if canonical_events_path.exists():
        canonical_data = load_yaml(canonical_events_path)
        canonical_events = canonical_data.get('canonical_events', {})
    
    # Collect all operation IDs from bundled contracts
    all_operation_ids = set()
    contract_files = {}
    
    if dist_dir.exists():
        for contract_file in dist_dir.glob('*.bundled.yaml'):
            contract_data = load_yaml(contract_file)
            ops = find_operation_ids_in_contract(contract_data)
            all_operation_ids.update(ops)
            contract_files[contract_file.name] = ops
            if verbose:
                print(f"  Found {len(ops)} operations in {contract_file.name}")
    else:
        return False, [f"Bundled contracts directory not found: {dist_dir}"], {}
    
    # Validate each domain's requirements
    violations = []
    stats = {
        'total_requirements': 0,
        'implemented': 0,
        'missing': 0,
        'partial': 0,
        'critical_missing': 0,
        'domains_checked': 0
    }
    
    # Domains to check (excluding metadata and statistics sections)
    domain_sections = [
        'authentication', 'attribution', 'reconciliation', 'export', 'health',
        'webhooks_shopify', 'webhooks_stripe', 'webhooks_woocommerce', 'webhooks_paypal'
    ]
    
    for domain_name in domain_sections:
        if domain_name not in manifest:
            continue
        
        domain = manifest[domain_name]
        stats['domains_checked'] += 1
        
        requirements = domain.get('requirements', [])
        for req in requirements:
            req_id = req.get('requirement_id', 'UNKNOWN')
            operation_id = req.get('operation_id')
            status = req.get('status', 'unknown')
            priority = req.get('priority', 'unknown')
            description = req.get('description', 'No description')
            canonical_event = req.get('canonical_event')  # Phase C2: canonical event linkage
            
            stats['total_requirements'] += 1
            
            # Count by status
            if status == 'implemented':
                stats['implemented'] += 1
                # Verify operation exists
                if operation_id not in all_operation_ids:
                    violation = (
                        f"{RED}X{NC} {req_id} ({priority}): Status is 'implemented' but "
                        f"operation '{operation_id}' NOT FOUND in contracts"
                    )
                    violations.append(violation)
                    if priority == 'critical':
                        stats['critical_missing'] += 1
            
            elif status == 'missing':
                stats['missing'] += 1
                if priority == 'critical':
                    stats['critical_missing'] += 1
                    violation = (
                        f"{YELLOW}!{NC} {req_id} (CRITICAL): {description} - "
                        f"Operation '{operation_id}' marked as missing"
                    )
                    violations.append(violation)
            
            elif status == 'partial':
                stats['partial'] += 1
            
            # Phase C2: Validate canonical event linkage (for webhook requirements)
            if canonical_event and canonical_events:
                if canonical_event not in canonical_events:
                    violation = (
                        f"{RED}X{NC} {req_id}: References unknown canonical event '{canonical_event}'"
                    )
                    violations.append(violation)
    
    success = len(violations) == 0
    return success, violations, stats

def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate API coverage manifest against OpenAPI contracts'
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    args = parser.parse_args()
    
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    
    print(f"{GREEN}========================================{NC}")
    print(f"{GREEN}Skeldir API Coverage Validation{NC}")
    print(f"{GREEN}========================================{NC}")
    print()
    
    success, violations, stats = validate_coverage(repo_root, args.verbose)
    
    if args.json:
        result = {
            'success': success,
            'violations': [v.replace(RED, '').replace(YELLOW, '').replace(GREEN, '').replace(NC, '') 
                          for v in violations],
            'statistics': stats
        }
        print(json.dumps(result, indent=2))
        sys.exit(0 if success else 1)
    
    # Print statistics
    print(f"{GREEN}Coverage Statistics:{NC}")
    print(f"  Total Requirements: {stats['total_requirements']}")
    print(f"  Implemented: {stats['implemented']} ({stats['implemented']/stats['total_requirements']*100:.1f}%)")
    print(f"  Missing: {stats['missing']}")
    print(f"  Partial: {stats['partial']}")
    print(f"  Critical Missing: {stats['critical_missing']}")
    print(f"  Domains Checked: {stats['domains_checked']}")
    print()
    
    if violations:
        print(f"{RED}✗ Coverage Violations Found:{NC}")
        print()
        for violation in violations:
            print(f"  {violation}")
        print()
        print(f"{RED}========================================{NC}")
        print(f"{RED}✗ COVERAGE VALIDATION FAILED{NC}")
        print(f"{RED}========================================{NC}")
        print()
        print(f"{YELLOW}Action Required:{NC}")
        print(f"  1. Review missing/incorrect operations in coverage manifest")
        print(f"  2. Implement missing critical operations in contracts")
        print(f"  3. Update coverage manifest status after implementation")
        print()
        sys.exit(1)
    else:
        print(f"{GREEN}✓ All coverage validations passed{NC}")
        print()
        if stats['critical_missing'] > 0:
            print(f"{YELLOW}⚠ Warning: {stats['critical_missing']} critical requirements marked as missing{NC}")
            print(f"  These must be implemented before production deployment.")
            print()
        
        print(f"{GREEN}========================================{NC}")
        print(f"{GREEN}✓ COVERAGE VALIDATION COMPLETE{NC}")
        print(f"{GREEN}========================================{NC}")
        print()
        sys.exit(0)

if __name__ == '__main__':
    main()

