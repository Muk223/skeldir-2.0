#!/usr/bin/env python3
"""
Validates that bundled contracts have no external $ref references.
Bundled (dereferenced) contracts should be self-contained.
Exit code 0 = no external refs
Exit code 1 = external refs found
"""

import argparse
import json
import re
import sys
from pathlib import Path

EXTERNAL_REF_PATTERN = re.compile(r'\$ref:\s*[\'"]?([^\'"\s]+)[\'"]?')

def check_file_for_external_refs(filepath: Path) -> list:
    """Check a single file for external $ref patterns."""
    external_refs = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            matches = EXTERNAL_REF_PATTERN.findall(line)
            for match in matches:
                # External refs start with ./ or ../ or contain file paths
                if match.startswith('./') or match.startswith('../') or '.yaml' in match or '.yml' in match:
                    external_refs.append({
                        "file": str(filepath),
                        "line": line_num,
                        "ref": match
                    })

    return external_refs

def main():
    parser = argparse.ArgumentParser(description="Assert no external refs in bundled contracts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    dist_dir = Path("api-contracts/dist/openapi/v1")

    if not dist_dir.exists():
        if args.json:
            print(json.dumps({"error": "dist directory does not exist", "path": str(dist_dir)}))
        else:
            print(f"ERROR: Distribution directory does not exist: {dist_dir}")
        sys.exit(1)

    all_external_refs = []
    files_checked = 0

    for bundle_file in dist_dir.glob("*.bundled.yaml"):
        files_checked += 1
        refs = check_file_for_external_refs(bundle_file)
        all_external_refs.extend(refs)

    if args.json:
        result = {
            "files_checked": files_checked,
            "external_refs_found": len(all_external_refs),
            "details": all_external_refs,
            "valid": len(all_external_refs) == 0
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"External reference check:")
        print(f"  Files checked: {files_checked}")
        print(f"  External refs: {len(all_external_refs)}")

        if all_external_refs:
            print("\nExternal references found:")
            for ref in all_external_refs:
                print(f"  {ref['file']}:{ref['line']} -> {ref['ref']}")
        else:
            print("\n✓ No external references (bundles fully dereferenced)")

    sys.exit(0 if len(all_external_refs) == 0 else 1)

if __name__ == "__main__":
    main()
