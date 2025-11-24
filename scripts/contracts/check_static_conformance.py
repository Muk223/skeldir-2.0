#!/usr/bin/env python3
"""
Static Contract Conformance Checker - Phase CF3

This script enforces bidirectional equivalence between implementation routes (R-Graph)
and contract operations (C-Graph), ensuring contract-first alignment.

Checks Performed:
1. Implementation → Contract: No undeclared routes (R_only must be empty)
2. Contract → Implementation: No phantom operations (C_only must be empty, minus allowlist)
3. Parameter Consistency: Path and query parameter names match for all aligned operations

Exit Codes:
- 0: All checks pass (perfect alignment)
- 1: Divergence detected (with diagnostic output)

This is the cornerstone of contract-first enforcement: any divergence blocks CI.
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


def load_scope_config() -> Dict:
    """Load contract scope configuration."""
    config_path = Path(__file__).parent.parent.parent / "backend" / "app" / "config" / "contract_scope.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Scope configuration not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_r_graph() -> Dict:
    """Load implementation route graph (R-Graph)."""
    r_graph_path = Path(__file__).parent.parent.parent / "tmp" / "r_graph.json"
    
    if not r_graph_path.exists():
        print(f"ERROR: R-Graph not found at {r_graph_path}", file=sys.stderr)
        print("Please run: python scripts/contracts/dump_routes.py", file=sys.stderr)
        sys.exit(1)
    
    with open(r_graph_path, 'r') as f:
        return json.load(f)


def load_c_graph() -> Dict:
    """Load contract operations graph (C-Graph)."""
    c_graph_path = Path(__file__).parent.parent.parent / "tmp" / "c_graph.json"
    
    if not c_graph_path.exists():
        print(f"ERROR: C-Graph not found at {c_graph_path}", file=sys.stderr)
        print("Please run: python scripts/contracts/dump_contract_ops.py", file=sys.stderr)
        sys.exit(1)
    
    with open(c_graph_path, 'r') as f:
        return json.load(f)


def normalize_path(path: str) -> str:
    """Normalize path for comparison (handle trailing slashes, etc.)."""
    return path.rstrip('/')


def make_operation_key(method: str, path: str) -> Tuple[str, str]:
    """Create canonical key for operation matching."""
    return (method.upper(), normalize_path(path))


def check_static_conformance() -> int:
    """
    Perform static conformance checks between R-Graph and C-Graph.
    
    Returns:
        0 if all checks pass, 1 if any divergence detected
    """
    print("=" * 80)
    print("Contract-First Enforcement: Static Conformance Check")
    print("=" * 80)
    print()
    
    config = load_scope_config()
    r_graph = load_r_graph()
    c_graph = load_c_graph()
    
    # Build operation sets
    r_operations = {}  # {(method, path): route_data}
    c_operations = {}  # {(method, path): operation_data}
    
    for route in r_graph.get('routes', []):
        key = make_operation_key(route['method'], route['path'])
        r_operations[key] = route
    
    for operation in c_graph.get('operations', []):
        key = make_operation_key(operation['method'], operation['path'])
        c_operations[key] = operation
    
    # Get sets of keys
    r_keys = set(r_operations.keys())
    c_keys = set(c_operations.keys())
    
    # Get contract-only allowlist
    allowlist_raw = config.get('contract_only_allowlist', [])
    allowlist = set()
    for item in allowlist_raw:
        if isinstance(item, str) and ' ' in item:
            parts = item.split(' ', 1)
            if len(parts) == 2:
                method, path = parts
                allowlist.add(make_operation_key(method, path))
    
    # Perform checks
    has_errors = False
    
    # Check 1: Implementation → Contract (no undeclared routes)
    print("Check 1: Implementation → Contract (No Undeclared Routes)")
    print("-" * 80)
    r_only = r_keys - c_keys
    
    if r_only:
        has_errors = True
        print(f"✗ FAIL: Found {len(r_only)} undeclared implementation route(s)")
        print()
        print("These routes exist in FastAPI but have no corresponding OpenAPI contract:")
        for method, path in sorted(r_only):
            route_info = r_operations[(method, path)]
            print(f"  {method:6s} {path}")
            print(f"         Operation ID: {route_info.get('operation_id', 'N/A')}")
            print(f"         Source: {route_info.get('name', 'unknown')}")
        print()
        print("ACTION REQUIRED: Either:")
        print("  1. Add OpenAPI contract for these routes, OR")
        print("  2. Remove these routes from implementation, OR")
        print("  3. Mark as out-of-scope in contract_scope.yaml (if they're internal)")
        print()
    else:
        print("✓ PASS: All implementation routes have corresponding contracts")
        print()
    
    # Check 2: Contract → Implementation (no phantom operations)
    print("Check 2: Contract → Implementation (No Phantom Operations)")
    print("-" * 80)
    c_only = c_keys - r_keys
    c_only_filtered = c_only - allowlist  # Remove explicitly allowed contract-only ops
    
    if c_only_filtered:
        has_errors = True
        print(f"✗ FAIL: Found {len(c_only_filtered)} unimplemented contract operation(s)")
        print()
        print("These operations are defined in OpenAPI but not implemented in FastAPI:")
        for method, path in sorted(c_only_filtered):
            op_info = c_operations[(method, path)]
            print(f"  {method:6s} {path}")
            print(f"         Operation ID: {op_info.get('operation_id', 'N/A')}")
            print(f"         Source: {op_info.get('source_bundle', 'unknown')}")
        print()
        print("ACTION REQUIRED: Either:")
        print("  1. Implement these operations in FastAPI, OR")
        print("  2. Remove from OpenAPI contracts, OR")
        print("  3. Add to contract_only_allowlist (if they're upcoming features)")
        print()
    else:
        if allowlist:
            print(f"✓ PASS: All contract operations implemented (excluding {len(allowlist)} allowlisted)")
        else:
            print("✓ PASS: All contract operations are implemented")
        print()
    
    # Check 3: Parameter Consistency (for matched operations)
    print("Check 3: Parameter Consistency (Matched Operations)")
    print("-" * 80)
    matched_ops = r_keys & c_keys
    param_errors = []
    
    for method, path in sorted(matched_ops):
        route = r_operations[(method, path)]
        operation = c_operations[(method, path)]
        
        # Check path parameters
        r_path_params = set(route.get('path_params', []))
        c_path_params = set(operation.get('path_params', []))
        
        if r_path_params != c_path_params:
            param_errors.append({
                'method': method,
                'path': path,
                'type': 'path_params',
                'implementation': sorted(r_path_params),
                'contract': sorted(c_path_params),
                'missing_in_impl': sorted(c_path_params - r_path_params),
                'missing_in_contract': sorted(r_path_params - c_path_params)
            })
        
        # Check query parameters (names only, not types/required for now)
        r_query_params = set(p['name'] for p in route.get('query_params', []))
        c_query_params = set(p['name'] for p in operation.get('query_params', []))
        
        if r_query_params != c_query_params:
            param_errors.append({
                'method': method,
                'path': path,
                'type': 'query_params',
                'implementation': sorted(r_query_params),
                'contract': sorted(c_query_params),
                'missing_in_impl': sorted(c_query_params - r_query_params),
                'missing_in_contract': sorted(r_query_params - c_query_params)
            })
    
    if param_errors:
        has_errors = True
        print(f"✗ FAIL: Found {len(param_errors)} parameter mismatch(es)")
        print()
        for error in param_errors:
            print(f"  {error['method']:6s} {error['path']}")
            print(f"         Mismatch Type: {error['type']}")
            print(f"         Implementation: {error['implementation']}")
            print(f"         Contract: {error['contract']}")
            if error['missing_in_impl']:
                print(f"         Missing in Impl: {error['missing_in_impl']}")
            if error['missing_in_contract']:
                print(f"         Missing in Contract: {error['missing_in_contract']}")
            print()
        print("ACTION REQUIRED: Align parameter names between implementation and contract")
        print()
    else:
        print(f"✓ PASS: All {len(matched_ops)} matched operations have consistent parameters")
        print()
    
    # Final Summary
    print("=" * 80)
    if has_errors:
        print("✗ STATIC CONFORMANCE CHECK FAILED")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Undeclared routes: {len(r_only)}")
        print(f"  - Unimplemented operations: {len(c_only_filtered)}")
        print(f"  - Parameter mismatches: {len(param_errors)}")
        print()
        print("Contract-first enforcement requires perfect alignment.")
        print("Implementation cannot diverge from specification.")
        return 1
    else:
        print("✓ STATIC CONFORMANCE CHECK PASSED")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Total implementation routes: {len(r_keys)}")
        print(f"  - Total contract operations: {len(c_keys)}")
        print(f"  - Matched operations: {len(matched_ops)}")
        print(f"  - Allowlisted contract-only: {len(allowlist)}")
        print()
        print("✓ Implementation and contracts are perfectly aligned")
        return 0


if __name__ == '__main__':
    sys.exit(check_static_conformance())



