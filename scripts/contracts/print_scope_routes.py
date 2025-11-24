#!/usr/bin/env python3
"""
Route Classification Utility - Phase CF0

This script loads the FastAPI application and classifies all routes as:
- in-scope: Governed by contract-first enforcement
- out-of-scope: Explicitly excluded from enforcement
- unknown: Missing classification (causes validation failure)

Exit Gates:
- Every route must be classified (zero "unknown" routes)
- Output is deterministic and machine-readable
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set
import fnmatch

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


def load_scope_config() -> Dict:
    """Load contract scope configuration."""
    config_path = Path(__file__).parent.parent.parent / "backend" / "app" / "config" / "contract_scope.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Scope configuration not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches pattern (supports ** wildcards)."""
    # Convert ** to * for fnmatch
    pattern = pattern.replace('/**', '/*')
    return fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip('*'))


def classify_route(path: str, config: Dict) -> str:
    """
    Classify a route as in-scope, out-of-scope, or unknown.
    
    Classification rules:
    1. Check out-of-scope paths first (explicit exclusions)
    2. Check in-scope prefixes
    3. Otherwise: unknown (validation failure)
    """
    # Check out-of-scope paths
    for out_path in config.get('out_of_scope_paths', []):
        if matches_pattern(path, out_path):
            return 'out-of-scope'
    
    # Check in-scope prefixes
    for prefix in config.get('in_scope_prefixes', []):
        if path.startswith(prefix):
            return 'in-scope'
    
    return 'unknown'


def print_routes_classification():
    """
    Load FastAPI app and classify all routes.
    
    Exit code 0: All routes classified
    Exit code 1: Unknown routes found or app cannot be loaded
    """
    config = load_scope_config()
    
    try:
        # Import FastAPI app
        from app.main import app
    except ImportError as e:
        print(f"ERROR: Cannot import FastAPI app: {e}", file=sys.stderr)
        print("Please ensure backend/app/main.py exists and app is defined", file=sys.stderr)
        sys.exit(1)
    
    # Collect routes
    routes_by_classification = {
        'in-scope': [],
        'out-of-scope': [],
        'unknown': []
    }
    
    for route in app.routes:
        # Skip non-route objects (middleware, mounts, etc.)
        if not hasattr(route, 'methods') or not hasattr(route, 'path'):
            continue
        
        path = route.path
        methods = route.methods or {'GET'}  # Default to GET if not specified
        
        classification = classify_route(path, config)
        
        for method in methods:
            if method in ('HEAD', 'OPTIONS'):  # Skip auto-generated methods
                continue
            routes_by_classification[classification].append({
                'method': method,
                'path': path,
                'name': route.name if hasattr(route, 'name') else 'unknown'
            })
    
    # Print results
    print("=" * 80)
    print("FastAPI Route Classification Report")
    print("=" * 80)
    print()
    
    print(f"IN-SCOPE ROUTES ({len(routes_by_classification['in-scope'])} total)")
    print("-" * 80)
    for route in sorted(routes_by_classification['in-scope'], key=lambda r: (r['path'], r['method'])):
        print(f"  {route['method']:6s} {route['path']:50s} ({route['name']})")
    print()
    
    print(f"OUT-OF-SCOPE ROUTES ({len(routes_by_classification['out-of-scope'])} total)")
    print("-" * 80)
    for route in sorted(routes_by_classification['out-of-scope'], key=lambda r: (r['path'], r['method'])):
        print(f"  {route['method']:6s} {route['path']:50s} ({route['name']})")
    print()
    
    print(f"UNKNOWN ROUTES ({len(routes_by_classification['unknown'])} total)")
    print("-" * 80)
    if routes_by_classification['unknown']:
        for route in sorted(routes_by_classification['unknown'], key=lambda r: (r['path'], r['method'])):
            print(f"  {route['method']:6s} {route['path']:50s} ({route['name']})")
        print()
        print("ERROR: Found routes with unknown classification!", file=sys.stderr)
        print("All routes must be either in-scope or explicitly out-of-scope.", file=sys.stderr)
        print("Update backend/app/config/contract_scope.yaml to classify these routes.", file=sys.stderr)
        sys.exit(1)
    else:
        print("  (none - all routes are classified)")
    
    print()
    print("=" * 80)
    print("✓ PASS: All routes are classified")
    print("=" * 80)
    
    # Summary
    total = len(routes_by_classification['in-scope']) + len(routes_by_classification['out-of-scope'])
    print(f"\nSummary: {total} routes classified")
    print(f"  - In-scope: {len(routes_by_classification['in-scope'])}")
    print(f"  - Out-of-scope: {len(routes_by_classification['out-of-scope'])}")
    print(f"  - Unknown: {len(routes_by_classification['unknown'])}")


if __name__ == '__main__':
    print_routes_classification()



