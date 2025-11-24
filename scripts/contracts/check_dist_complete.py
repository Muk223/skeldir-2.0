#!/usr/bin/env python3
"""
Contract Distribution Completeness Checker

Validates that all entrypoints defined in the manifest have corresponding
bundled output files in the distribution directory.

Usage:
    python scripts/contracts/check_dist_complete.py [--json]

Exit Codes:
    0: All bundles present
    1: One or more bundles missing

Output:
    --json flag: Structured JSON output for CI consumption
    default: Human-readable output with colors
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


def load_manifest(manifest_path: Path) -> Dict:
    """Load and parse the entrypoints manifest."""
    if not manifest_path.exists():
        print(f"{Colors.RED}ERROR: Manifest not found: {manifest_path}{Colors.NC}", file=sys.stderr)
        sys.exit(2)
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        return manifest
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}ERROR: Invalid JSON in manifest: {e}{Colors.NC}", file=sys.stderr)
        sys.exit(2)


def check_completeness(manifest: Dict, repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Check if all bundled files exist.
    
    Returns:
        (present_files, missing_files) tuple of lists
    """
    entrypoints = manifest.get('entrypoints', [])
    
    if not entrypoints:
        print(f"{Colors.YELLOW}WARNING: No entrypoints defined in manifest{Colors.NC}", file=sys.stderr)
        return [], []
    
    present = []
    missing = []
    
    for entry in entrypoints:
        entry_id = entry.get('id', 'unknown')
        bundle_path = entry.get('bundle')
        
        if not bundle_path:
            print(f"{Colors.YELLOW}WARNING: No bundle path for entrypoint '{entry_id}'{Colors.NC}", file=sys.stderr)
            continue
        
        full_path = repo_root / bundle_path
        
        if full_path.exists() and full_path.is_file():
            present.append(bundle_path)
        else:
            missing.append(bundle_path)
    
    return present, missing


def main():
    parser = argparse.ArgumentParser(
        description='Check completeness of bundled OpenAPI contracts'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format for CI consumption'
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        default=Path('scripts/contracts/entrypoints.json'),
        help='Path to entrypoints manifest (default: scripts/contracts/entrypoints.json)'
    )
    
    args = parser.parse_args()
    
    # Determine repository root (parent of scripts directory)
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent
    
    # Load manifest
    manifest_path = repo_root / args.manifest
    manifest = load_manifest(manifest_path)
    
    # Check completeness
    present, missing = check_completeness(manifest, repo_root)
    
    # Prepare output
    total = len(present) + len(missing)
    result = {
        'total_expected': total,
        'present': len(present),
        'missing': len(missing),
        'present_files': present,
        'missing_files': missing,
        'status': 'complete' if not missing else 'incomplete'
    }
    
    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if missing:
            print(f"{Colors.RED}X INCOMPLETE: {len(missing)}/{total} bundles missing{Colors.NC}")
            print()
            print("Missing bundles:")
            for bundle in missing:
                print(f"  {Colors.RED}X{Colors.NC} {bundle}")
            print()
            print("Present bundles:")
            for bundle in present:
                print(f"  {Colors.GREEN}+{Colors.NC} {bundle}")
        else:
            print(f"{Colors.GREEN}+ COMPLETE: All {total} bundles present{Colors.NC}")
            for bundle in present:
                print(f"  {Colors.GREEN}+{Colors.NC} {bundle}")
    
    # Exit with appropriate code
    sys.exit(0 if not missing else 1)


if __name__ == '__main__':
    main()

