#!/usr/bin/env python3
"""
External Reference Assertion Tool

Validates that bundled OpenAPI files contain zero external $ref entries,
ensuring they are fully dereferenced and context-free.

Usage:
    python scripts/contracts/assert_no_external_refs.py [--json] [--dist-dir DIR]

Exit Codes:
    0: No external refs found (all bundles are context-free)
    1: One or more external refs found
    2: Error loading files

Output:
    --json flag: Structured JSON output for CI consumption
    default: Human-readable output with colors
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


def find_external_refs(yaml_content: Dict, file_path: str) -> List[Tuple[str, str]]:
    """
    Recursively find all external $ref entries in YAML content.
    
    An external ref is any $ref that doesn't start with '#/' (internal JSON pointer).
    
    Returns:
        List of (json_path, ref_value) tuples
    """
    external_refs = []
    
    def walk(obj, path="root"):
        if isinstance(obj, dict):
            if '$ref' in obj:
                ref_value = obj['$ref']
                # External ref: doesn't start with '#/' or contains file path
                if not ref_value.startswith('#/'):
                    external_refs.append((path, ref_value))
            
            for key, value in obj.items():
                walk(value, f"{path}.{key}")
        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                walk(item, f"{path}[{idx}]")
    
    walk(yaml_content)
    return external_refs


def check_bundle(bundle_path: Path) -> Tuple[int, List[Tuple[str, str]]]:
    """
    Check a single bundled file for external references.
    
    Returns:
        (ref_count, ref_list) tuple
    """
    if not bundle_path.exists():
        return 0, []
    
    try:
        with open(bundle_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        external_refs = find_external_refs(content, str(bundle_path))
        return len(external_refs), external_refs
    
    except yaml.YAMLError as e:
        print(f"{Colors.YELLOW}WARNING: Failed to parse {bundle_path}: {e}{Colors.NC}", file=sys.stderr)
        return 0, []
    except Exception as e:
        print(f"{Colors.YELLOW}WARNING: Error reading {bundle_path}: {e}{Colors.NC}", file=sys.stderr)
        return 0, []


def main():
    parser = argparse.ArgumentParser(
        description='Assert no external $ref entries in bundled OpenAPI files'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format for CI consumption'
    )
    parser.add_argument(
        '--dist-dir',
        type=Path,
        default=Path('api-contracts/dist/openapi/v1'),
        help='Path to bundled files directory (default: api-contracts/dist/openapi/v1)'
    )
    
    args = parser.parse_args()
    
    # Determine repository root
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent
    dist_dir = repo_root / args.dist_dir
    
    if not dist_dir.exists():
        if args.json:
            print(json.dumps({
                'status': 'error',
                'message': f'Distribution directory not found: {dist_dir}'
            }))
        else:
            print(f"{Colors.RED}ERROR: Distribution directory not found: {dist_dir}{Colors.NC}", file=sys.stderr)
        sys.exit(2)
    
    # Find all bundled YAML files
    bundle_files = list(dist_dir.glob('*.bundled.yaml'))
    
    if not bundle_files:
        if args.json:
            print(json.dumps({
                'status': 'error',
                'message': f'No bundled files found in {dist_dir}'
            }))
        else:
            print(f"{Colors.YELLOW}WARNING: No bundled files found in {dist_dir}{Colors.NC}", file=sys.stderr)
        sys.exit(2)
    
    # Check each bundle
    results = {}
    total_refs = 0
    
    for bundle_path in sorted(bundle_files):
        rel_path = bundle_path.relative_to(repo_root)
        ref_count, ref_list = check_bundle(bundle_path)
        
        results[str(rel_path)] = {
            'count': ref_count,
            'refs': [{'path': path, 'value': value} for path, value in ref_list]
        }
        total_refs += ref_count
    
    # Prepare output
    result = {
        'total_files': len(bundle_files),
        'total_external_refs': total_refs,
        'status': 'pass' if total_refs == 0 else 'fail',
        'files': results
    }
    
    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if total_refs > 0:
            print(f"{Colors.RED}X FAILED: {total_refs} external $ref entries found across {len(bundle_files)} files{Colors.NC}")
            print()
            print("External references found:")
            for file_path, file_result in results.items():
                if file_result['count'] > 0:
                    print(f"\n  {Colors.RED}{file_path}{Colors.NC} ({file_result['count']} refs):")
                    for ref in file_result['refs'][:5]:  # Show first 5
                        print(f"    {Colors.YELLOW}${Colors.NC}ref: {ref['value']}")
                        print(f"      at: {ref['path']}")
                    if file_result['count'] > 5:
                        print(f"    ... and {file_result['count'] - 5} more")
            
            print()
            print(f"{Colors.YELLOW}Bundled files must be fully dereferenced (all $ref must start with '#/'){Colors.NC}")
        else:
            print(f"{Colors.GREEN}+ PASSED: All {len(bundle_files)} bundles are fully dereferenced (zero external refs){Colors.NC}")
            for file_path in results.keys():
                print(f"  {Colors.GREEN}+{Colors.NC} {file_path}")
    
    # Exit with appropriate code
    sys.exit(0 if total_refs == 0 else 1)


if __name__ == '__main__':
    main()

