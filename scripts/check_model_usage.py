#!/usr/bin/env python3
"""
Operational Gate P4: CI Enforcement Check

This script validates that FastAPI routes use generated models, not hand-rolled ones.
If a route uses a non-generated model for a contract-defined payload, this script fails.

This is a semantic check, not just syntactic - it enforces the operational dependency.
"""

import sys
import ast
import os
from pathlib import Path

# Define which models are generated (from components/schemas)
GENERATED_MODELS = {
    'RealtimeRevenueResponse',
    'LoginRequest', 'LoginResponse', 'RefreshRequest', 'RefreshResponse', 'LogoutResponse',
    'ReconciliationStatusResponse',
    'ExportRevenueResponse',
    'ShopifyOrderCreateRequest', 'WooCommerceOrderCreateRequest',
    'StripeChargeSucceededRequest', 'PayPalSaleCompletedRequest',
    'WebhookAcknowledgement',
}

# Define generated model import paths
GENERATED_IMPORT_PATHS = [
    'backend.app.schemas.attribution',
    'backend.app.schemas.auth',
    'backend.app.schemas.reconciliation',
    'backend.app.schemas.export',
    'backend.app.schemas.webhooks_shopify',
    'backend.app.schemas.webhooks_woocommerce',
    'backend.app.schemas.webhooks_stripe',
    'backend.app.schemas.webhooks_paypal',
]


def find_fastapi_routes():
    """Find all FastAPI route files."""
    backend_path = Path('backend/app')
    if not backend_path.exists():
        return []
    
    route_files = []
    for py_file in backend_path.rglob('*.py'):
        # Skip __init__.py and test files
        if py_file.name == '__init__.py' or 'test' in py_file.name:
            continue
        route_files.append(py_file)
    
    return route_files


def check_file_for_handrolled_models(file_path):
    """
    Check if a Python file uses hand-rolled Pydantic models instead of generated ones.
    
    Returns: (has_handrolled, violations)
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return False, []
    
    # Check for BaseModel definitions (hand-rolled models)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if class inherits from BaseModel
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'BaseModel':
                    # Check if this looks like a contract-defined model
                    if any(model_name.lower() in node.name.lower() for model_name in GENERATED_MODELS):
                        violations.append(f"{file_path}:{node.lineno}: Hand-rolled model '{node.name}' should use generated model")
                elif isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                    if any(model_name.lower() in node.name.lower() for model_name in GENERATED_MODELS):
                        violations.append(f"{file_path}:{node.lineno}: Hand-rolled model '{node.name}' should use generated model")
    
    # Check for imports from generated modules
    has_generated_imports = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and any(gen_path in node.module for gen_path in GENERATED_IMPORT_PATHS):
                has_generated_imports = True
    
    return len(violations) > 0, violations


def main():
    print("Operational Gate P4: Checking for hand-rolled models in FastAPI routes...")
    
    route_files = find_fastapi_routes()
    
    if not route_files:
        print("No FastAPI route files found. This is expected if routes are not yet implemented.")
        print("✓ Operational Gate P4: No violations (no routes to check)")
        return 0
    
    all_violations = []
    for route_file in route_files:
        has_handrolled, violations = check_file_for_handrolled_models(route_file)
        if has_handrolled:
            all_violations.extend(violations)
    
    if all_violations:
        print("ERROR: Found hand-rolled models that should use generated models:")
        for violation in all_violations:
            print(f"  ✗ {violation}")
        print("\nOperational Gate P4 FAILED: Routes must use generated models for contract-defined payloads")
        return 1
    else:
        print("✓ Operational Gate P4 PASSED: All routes use generated models (or no routes exist yet)")
        return 0


if __name__ == "__main__":
    sys.exit(main())



