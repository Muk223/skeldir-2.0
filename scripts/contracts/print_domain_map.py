#!/usr/bin/env python3
"""
Forensic Domain Mapping Script
Phase 0: Baseline Assessment

Maps contract bundles to API domains and ports for mock servers.
Identifies primary vs on-demand mocks based on Replit constraints.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_entrypoints(repo_root: Path) -> List[Dict[str, str]]:
    """Load entrypoints manifest."""
    manifest_path = repo_root / "scripts" / "contracts" / "entrypoints.json"
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    
    return data.get('entrypoints', [])


def load_scope_config(repo_root: Path) -> Dict[str, Any]:
    """Load contract scope configuration."""
    scope_path = repo_root / "backend" / "app" / "config" / "contract_scope.yaml"
    if not scope_path.exists():
        print(f"WARNING: Scope config not found: {scope_path}", file=sys.stderr)
        return {'in_scope_prefixes': [], 'spec_mappings': {}}
    
    import yaml
    with open(scope_path, 'r') as f:
        return yaml.safe_load(f)


def load_mock_registry(repo_root: Path) -> Dict[str, Any]:
    """Load mock registry configuration (if exists)."""
    registry_path = repo_root / "scripts" / "contracts" / "mock_registry.json"
    if not registry_path.exists():
        # Return default configuration
        return {
            "primary_mocks": ["auth", "attribution", "health"],
            "port_mapping": {
                "auth": 4010,
                "attribution": 4011,
                "health": 4012
            },
            "on_demand_port": 4013,
            "replit_constraints": {
                "max_concurrent": 3,
                "reason": "Port exposure limits"
            }
        }
    
    with open(registry_path, 'r') as f:
        return json.load(f)


def extract_domain_from_id(entry_id: str) -> str:
    """Extract clean domain name from entry ID."""
    # Remove webhooks_ prefix for webhook domains
    if entry_id.startswith('webhooks_'):
        return entry_id.replace('webhooks_', 'webhooks.')
    return entry_id


def main():
    """Generate domain mapping report."""
    repo_root = Path(__file__).parent.parent.parent
    
    print("=" * 80)
    print("FORENSIC DOMAIN MAPPING - Phase 0 Baseline Assessment")
    print("=" * 80)
    print()
    
    # Load configurations
    entrypoints = load_entrypoints(repo_root)
    scope_config = load_scope_config(repo_root)
    mock_registry = load_mock_registry(repo_root)
    
    print(f"Total Contract Bundles: {len(entrypoints)}")
    print(f"In-Scope Prefixes: {len(scope_config.get('in_scope_prefixes', []))}")
    print(f"Primary Mocks (Replit Limit): {len(mock_registry.get('primary_mocks', []))}")
    print()
    
    # Map domains
    print("=" * 80)
    print("DOMAIN -> BUNDLE -> PORT MAPPING")
    print("=" * 80)
    print()
    
    primary_mocks = mock_registry.get('primary_mocks', [])
    port_mapping = mock_registry.get('port_mapping', {})
    on_demand_port = mock_registry.get('on_demand_port', 4013)
    
    primary_count = 0
    on_demand_count = 0
    
    for entry in entrypoints:
        entry_id = entry['id']
        domain = extract_domain_from_id(entry_id)
        bundle_path = entry['bundle']
        
        # Check if bundle exists
        full_path = repo_root / bundle_path
        exists = "[OK]" if full_path.exists() else "[MISSING]"
        
        # Determine if primary or on-demand
        is_primary = entry_id in primary_mocks
        if is_primary:
            port = port_mapping.get(entry_id, 'N/A')
            status = "PRIMARY"
            primary_count += 1
        else:
            port = on_demand_port
            status = "ON-DEMAND"
            on_demand_count += 1
        
        print(f"{exists:10s} {domain:25s} -> Port {port:4} [{status:9s}]")
        print(f"   Bundle: {bundle_path}")
        
        # Check scope mapping
        scope_mapped = False
        for prefix, spec in scope_config.get('spec_mappings', {}).items():
            if spec == bundle_path:
                scope_mapped = True
                print(f"   Scope:  {prefix}")
                break
        
        if not scope_mapped:
            print(f"   Scope:  [NOT MAPPED - WARNING]")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Domains:        {len(entrypoints)}")
    print(f"Primary Mocks:        {primary_count} (auto-start)")
    print(f"On-Demand Mocks:      {on_demand_count} (manual switch)")
    print(f"Replit Constraint:    Max {mock_registry.get('replit_constraints', {}).get('max_concurrent', 3)} concurrent")
    print()
    
    # Validation
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print()
    
    all_exist = all((repo_root / e['bundle']).exists() for e in entrypoints)
    all_mapped = all(
        any(spec == e['bundle'] for spec in scope_config.get('spec_mappings', {}).values())
        for e in entrypoints
    )
    
    if all_exist:
        print("[PASS] All bundles exist")
    else:
        print("[FAIL] Some bundles missing - run `bash scripts/contracts/bundle.sh`")
    
    if all_mapped:
        print("[PASS] All domains mapped in scope config")
    else:
        print("[WARN] Some domains not in scope config - review contract_scope.yaml")
    
    print()
    
    # Current vs Target State
    print("=" * 80)
    print("ARCHITECTURAL DIVERGENCE")
    print("=" * 80)
    print()
    print("CURRENT STATE (Docker Compose):")
    print("  - Mocks bind to: contracts/*/v1/*.yaml (source files)")
    print("  - Docker infrastructure: docker-compose.yml")
    print("  - Port range: 4010-4018 (9 containers)")
    print()
    print("TARGET STATE (Replit-Native):")
    print("  - Mocks bind to: api-contracts/dist/openapi/v1/*.bundled.yaml (validated artifacts)")
    print("  - Subprocess infrastructure: Prism CLI with process management")
    print("  - Port range: 4010-4013 (3 primary + 1 on-demand)")
    print()
    print("REMEDIATION REQUIRED:")
    print("  1. Replace Docker Compose with subprocess-based Prism execution")
    print("  2. Update mock binding from source files to bundled artifacts")
    print("  3. Implement 3-mock limit with on-demand switching for Replit")
    print()
    
    # Exit status
    if all_exist and all_mapped:
        print("[SUCCESS] Phase 0 Exit Gate P0.1: PASSED - Complete domain mapping generated")
        return 0
    else:
        print("[FAILURE] Phase 0 Exit Gate P0.1: FAILED - Incomplete mapping or missing bundles")
        return 1


if __name__ == '__main__':
    sys.exit(main())

