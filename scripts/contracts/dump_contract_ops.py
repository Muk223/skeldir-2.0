#!/usr/bin/env python3
"""
OpenAPI Contract Introspection - Phase CF2 (C-Graph Generation)

This script parses bundled OpenAPI specifications to generate a canonical, machine-readable
graph of contract-defined operations (C-Graph).

The C-Graph is used by check_static_conformance.py to validate bidirectional alignment
between contracts and implementation.

Output: tmp/c_graph.json - Deterministically sorted list of contract operations

Exit Gates:
- All in-scope bundled operations captured
- Spot-check confirms expected operations present
- Output includes: method, path, operationId, request/response schemas
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
import re


def load_scope_config() -> Dict:
    """Load contract scope configuration."""
    config_path = Path(__file__).parent.parent.parent / "backend" / "app" / "config" / "contract_scope.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Scope configuration not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def is_in_scope(path: str, config: Dict) -> bool:
    """Check if operation path is in-scope for contract enforcement."""
    # Check if explicitly out-of-scope
    for out_path in config.get('out_of_scope_paths', []):
        pattern = out_path.replace('/**', '/')
        if path.startswith(pattern.rstrip('*')):
            return False
    
    # Check if matches in-scope prefix
    for prefix in config.get('in_scope_prefixes', []):
        if path.startswith(prefix):
            return True
    
    return False


def extract_path_params(path: str, operation: Dict) -> List[str]:
    """Extract path parameter names from path template and operation parameters."""
    # Extract from path template (OpenAPI uses {param} format)
    params_from_path = set(re.findall(r'\{([^}]+)\}', path))
    
    # Also check parameters section for path params
    params_from_spec = set()
    if 'parameters' in operation:
        for param in operation['parameters']:
            if isinstance(param, dict) and param.get('in') == 'path':
                params_from_spec.add(param.get('name'))
    
    return sorted(params_from_path | params_from_spec)


def extract_query_params(operation: Dict) -> List[Dict[str, Any]]:
    """Extract query parameter names from operation parameters."""
    query_params = []
    
    if 'parameters' not in operation:
        return query_params
    
    for param in operation['parameters']:
        if isinstance(param, dict) and param.get('in') == 'query':
            query_params.append({
                'name': param.get('name'),
                'required': param.get('required', False)
            })
    
    return query_params


def extract_request_schema(operation: Dict) -> str:
    """Extract request body schema reference if present."""
    if 'requestBody' not in operation:
        return None
    
    request_body = operation['requestBody']
    if not isinstance(request_body, dict):
        return None
    
    content = request_body.get('content', {})
    json_content = content.get('application/json', {})
    schema = json_content.get('schema', {})
    
    # Try to get schema title or $ref
    if 'title' in schema:
        return schema['title']
    elif '$ref' in schema:
        # Extract schema name from $ref like #/components/schemas/LoginRequest
        ref = schema['$ref']
        return ref.split('/')[-1] if '/' in ref else ref
    
    return None


def extract_response_schemas(operation: Dict) -> Dict[str, str]:
    """Extract response schemas by status code."""
    response_schemas = {}
    
    if 'responses' not in operation:
        return response_schemas
    
    for status_code, response in operation['responses'].items():
        if not isinstance(response, dict):
            continue
        
        content = response.get('content', {})
        json_content = content.get('application/json', {})
        schema = json_content.get('schema', {})
        
        # Try to get schema title or $ref
        if 'title' in schema:
            response_schemas[status_code] = schema['title']
        elif '$ref' in schema:
            # Extract schema name from $ref
            ref = schema['$ref']
            response_schemas[status_code] = ref.split('/')[-1] if '/' in ref else ref
    
    return response_schemas


def parse_bundle(bundle_path: Path, config: Dict) -> List[Dict]:
    """Parse a single bundled OpenAPI spec and extract operations."""
    operations = []
    
    if not bundle_path.exists():
        print(f"Warning: Bundle not found: {bundle_path}", file=sys.stderr)
        return operations
    
    try:
        with open(bundle_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse {bundle_path}: {e}", file=sys.stderr)
        return operations
    
    if not spec or 'paths' not in spec:
        print(f"Warning: No paths found in {bundle_path}", file=sys.stderr)
        return operations
    
    # Extract operations from paths
    for path, path_item in spec['paths'].items():
        if not isinstance(path_item, dict):
            continue
        
        # Check if path is in scope
        if not is_in_scope(path, config):
            continue
        
        # Process each HTTP method
        for method in ['get', 'post', 'put', 'patch', 'delete']:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue
            
            operation_data = {
                'method': method.upper(),
                'path': path,
                'operation_id': operation.get('operationId'),
                'summary': operation.get('summary'),
                'tags': operation.get('tags', []),
                'path_params': extract_path_params(path, operation),
                'query_params': extract_query_params(operation),
                'request_schema': extract_request_schema(operation),
                'response_schemas': extract_response_schemas(operation),
                'source_bundle': bundle_path.name
            }
            
            operations.append(operation_data)
    
    return operations


def dump_contract_ops():
    """
    Parse all bundled OpenAPI specs and generate C-Graph.
    
    Exit code 0: C-Graph generated successfully
    Exit code 1: Bundles cannot be found or error occurred
    """
    config = load_scope_config()
    
    # Find all bundled specs
    bundles_dir = Path(__file__).parent.parent.parent / "api-contracts" / "dist" / "openapi" / "v1"
    
    if not bundles_dir.exists():
        print(f"ERROR: Bundled specs directory not found: {bundles_dir}", file=sys.stderr)
        print("Please run bundling pipeline first: ./scripts/contracts/pipeline.ps1", file=sys.stderr)
        sys.exit(1)
    
    # Get all .bundled.yaml files
    bundle_files = list(bundles_dir.glob("*.bundled.yaml"))
    
    if not bundle_files:
        print(f"ERROR: No bundled specs found in {bundles_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(bundle_files)} bundled specifications")
    
    all_operations = []
    
    for bundle_path in sorted(bundle_files):
        print(f"  Parsing {bundle_path.name}...")
        operations = parse_bundle(bundle_path, config)
        all_operations.extend(operations)
        print(f"    Found {len(operations)} in-scope operations")
    
    # Sort deterministically by (path, method)
    all_operations.sort(key=lambda op: (op['path'], op['method']))
    
    # Create output directory
    output_dir = Path(__file__).parent.parent.parent / "tmp"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "c_graph.json"
    
    # Write C-Graph
    with open(output_path, 'w') as f:
        json.dump({
            'operations': all_operations,
            'metadata': {
                'total_operations': len(all_operations),
                'generator': 'dump_contract_ops.py',
                'source': 'Bundled OpenAPI specifications',
                'bundles_processed': len(bundle_files)
            }
        }, f, indent=2, sort_keys=True)
    
    print(f"\n✓ Generated C-Graph: {output_path}")
    print(f"  Total in-scope operations: {len(all_operations)}")
    
    # Print summary by path
    for operation in all_operations:
        print(f"    {operation['method']:6s} {operation['path']}")
    
    return 0


if __name__ == '__main__':
    sys.exit(dump_contract_ops())



