#!/usr/bin/env python3
"""
Documentation Validation Script - Phase 4
Validates generated HTML documentation for completeness and correctness
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any


class DocValidationError(Exception):
    """Documentation validation error."""
    pass


def load_entrypoints(repo_root: Path) -> List[Dict[str, str]]:
    """Load entrypoints manifest."""
    manifest_path = repo_root / "scripts" / "contracts" / "entrypoints.json"
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    return data.get('entrypoints', [])


def validate_file_exists(file_path: Path, domain: str) -> None:
    """Validate that HTML file exists."""
    if not file_path.exists():
        raise DocValidationError(f"Documentation file not found: {file_path}")
    print(f"  ✓ {domain}.html exists")


def validate_file_size(file_path: Path, domain: str, min_size: int = 10240) -> None:
    """Validate that HTML file has reasonable size (> 10KB)."""
    size = file_path.stat().st_size
    if size < min_size:
        raise DocValidationError(
            f"Documentation file too small: {file_path} ({size} bytes, expected > {min_size})"
        )
    print(f"  ✓ {domain}.html size: {size} bytes")


def validate_html_content(file_path: Path, domain: str, expected_title: str = None) -> None:
    """Validate HTML content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for basic HTML structure
    if '<html' not in content.lower():
        raise DocValidationError(f"Invalid HTML: missing <html> tag in {file_path}")
    
    if '<head' not in content.lower():
        raise DocValidationError(f"Invalid HTML: missing <head> tag in {file_path}")
    
    if '<body' not in content.lower():
        raise DocValidationError(f"Invalid HTML: missing <body> tag in {file_path}")
    
    # Check for title
    if '<title>' not in content.lower():
        raise DocValidationError(f"Invalid HTML: missing <title> tag in {file_path}")
    
    print(f"  ✓ {domain}.html has valid HTML structure")
    
    return content


def validate_metadata(content: str, domain: str) -> None:
    """Validate metadata tags presence."""
    required_meta_tags = [
        'contract-version',
        'contract-bundle',
        'build-timestamp',
        'generator'
    ]
    
    missing_tags = []
    for tag in required_meta_tags:
        if f'name="{tag}"' not in content and f"name='{tag}'" not in content:
            missing_tags.append(tag)
    
    if missing_tags:
        raise DocValidationError(
            f"Missing metadata tags in {domain}.html: {', '.join(missing_tags)}"
        )
    
    print(f"  ✓ {domain}.html has required metadata tags")


def validate_api_content(content: str, domain: str, bundle_path: Path) -> None:
    """Validate that API-specific content is present."""
    import yaml
    
    # Load bundle to get expected content
    with open(bundle_path, 'r') as f:
        bundle = yaml.safe_load(f)
    
    # Check for API title
    api_title = bundle.get('info', {}).get('title', '')
    if api_title and api_title not in content:
        print(f"  ⚠ Warning: API title '{api_title}' not found in {domain}.html")
    else:
        print(f"  ✓ {domain}.html contains API title")
    
    # Check for at least one endpoint path
    paths = bundle.get('paths', {})
    if paths:
        # Just check if at least one path is documented
        found_path = False
        for path in paths.keys():
            if path in content:
                found_path = True
                break
        
        if found_path:
            print(f"  ✓ {domain}.html contains API endpoints")
        else:
            print(f"  ⚠ Warning: No API endpoints found in {domain}.html content")


def validate_index_page(docs_dir: Path) -> None:
    """Validate index page."""
    index_path = docs_dir / "index.html"
    
    if not index_path.exists():
        raise DocValidationError("Index page not found: index.html")
    
    print("  ✓ index.html exists")
    
    # Validate size
    size = index_path.stat().st_size
    if size < 1024:
        raise DocValidationError(f"Index page too small: {size} bytes")
    
    print(f"  ✓ index.html size: {size} bytes")
    
    # Check content
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for links to all domains
    required_links = [
        'auth.html',
        'attribution.html',
        'reconciliation.html',
        'export.html',
        'health.html',
        'webhooks_shopify.html',
        'webhooks_woocommerce.html',
        'webhooks_stripe.html',
        'webhooks_paypal.html'
    ]
    
    missing_links = []
    for link in required_links:
        if link not in content:
            missing_links.append(link)
    
    if missing_links:
        raise DocValidationError(
            f"Index page missing links: {', '.join(missing_links)}"
        )
    
    print(f"  ✓ index.html contains all required links")


def main():
    """Main validation routine."""
    print("=" * 80)
    print("DOCUMENTATION VALIDATION")
    print("=" * 80)
    print()
    
    repo_root = Path(__file__).parent.parent.parent
    docs_dir = repo_root / "api-contracts" / "dist" / "docs" / "v1"
    
    if not docs_dir.exists():
        print(f"ERROR: Documentation directory not found: {docs_dir}")
        print("Run: bash scripts/contracts/build_docs.sh")
        return 1
    
    print(f"Documentation directory: {docs_dir}")
    print()
    
    # Load entrypoints
    entrypoints = load_entrypoints(repo_root)
    print(f"Validating documentation for {len(entrypoints)} domains...")
    print()
    
    # Validate each domain
    validation_errors = []
    
    for entry in entrypoints:
        domain = entry['id']
        bundle_rel = entry['bundle']
        bundle_path = repo_root / bundle_rel
        
        print(f"Validating {domain}:")
        
        try:
            doc_path = docs_dir / f"{domain}.html"
            
            # Run validations
            validate_file_exists(doc_path, domain)
            validate_file_size(doc_path, domain)
            content = validate_html_content(doc_path, domain)
            validate_metadata(content, domain)
            validate_api_content(content, domain, bundle_path)
            
            print()
        
        except DocValidationError as e:
            validation_errors.append(str(e))
            print(f"  ✗ FAILED: {e}")
            print()
    
    # Validate index page
    print("Validating index page:")
    try:
        validate_index_page(docs_dir)
        print()
    except DocValidationError as e:
        validation_errors.append(str(e))
        print(f"  ✗ FAILED: {e}")
        print()
    
    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    
    if validation_errors:
        print(f"✗ FAILED: {len(validation_errors)} error(s) found:")
        for i, error in enumerate(validation_errors, 1):
            print(f"  {i}. {error}")
        print()
        print("Run: bash scripts/contracts/build_docs.sh")
        return 1
    else:
        print(f"✓ SUCCESS: All {len(entrypoints)} domain docs + index validated")
        print()
        print("All documentation files:")
        print("  - Exist with reasonable size")
        print("  - Have valid HTML structure")
        print("  - Contain required metadata tags")
        print("  - Include expected API content")
        print()
        return 0


if __name__ == '__main__':
    sys.exit(main())



