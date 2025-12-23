"""
Contract Integrity Test Suite - Phase 2
Schmidt's Phase B: Validate mocks serve contract-compliant responses

This test suite validates that:
1. Mock servers serve responses that conform to contract schemas
2. Examples in contracts are valid against their own schemas
3. Mock binding to bundled artifacts is functioning correctly

Test Sequence (Schmidt's Causal Chain):
  Phase 2 (Integrity): Mocks vs Contracts
  Phase 3 (Provider): Implementation vs Contracts

If integrity fails -> Contract has invalid examples
If integrity passes but provider fails -> Implementation divergence
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import pytest
import requests
import yaml


# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent
DIST_DIR = REPO_ROOT / "api-contracts" / "dist" / "openapi" / "v1"
REGISTRY_FILE = REPO_ROOT / "scripts" / "contracts" / "mock_registry.json"

# Timeouts and retries
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1


def load_mock_registry() -> Dict[str, Any]:
    """Load mock registry configuration."""
    with open(REGISTRY_FILE, 'r') as f:
        return json.load(f)


def load_bundle(bundle_path: Path) -> Dict[str, Any]:
    """Load and parse OpenAPI bundle."""
    with open(bundle_path, 'r') as f:
        return yaml.safe_load(f)


def get_primary_mocks() -> List[Dict[str, Any]]:
    """Get list of primary mocks that should be running."""
    registry = load_mock_registry()
    primary = registry['primary_mocks']
    port_mapping = registry['port_mapping']
    
    mocks = []
    for mock_id in primary:
        bundle_path = DIST_DIR / f"{mock_id}.bundled.yaml"
        if not bundle_path.exists():
            pytest.skip(f"Bundle not found: {bundle_path}")
        
        mocks.append({
            'id': mock_id,
            'port': port_mapping[mock_id],
            'bundle_path': bundle_path,
            'base_url': f"http://localhost:{port_mapping[mock_id]}"
        })
    
    return mocks


def extract_operations(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all operations from bundle."""
    operations = []
    paths = bundle.get('paths', {})
    
    for path, path_item in paths.items():
        common_parameters = path_item.get('parameters', [])
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            if method in path_item:
                operation = path_item[method]
                parameters = common_parameters + operation.get('parameters', [])
                operations.append({
                    'path': path,
                    'method': method.upper(),
                    'operation_id': operation.get('operationId', f"{method}_{path}"),
                    'operation': operation,
                    'parameters': parameters,
                    'requestBody': operation.get('requestBody', {}),
                    'responses': operation.get('responses', {})
                })
    
    return operations


def generate_sample_from_schema(schema: Dict[str, Any]) -> Any:
    """Recursively generate sample data that satisfies the provided schema."""
    if schema is None:
        return None

    if 'example' in schema:
        return schema['example']

    enum_values = schema.get('enum')
    if enum_values:
        return enum_values[0]

    schema_type = schema.get('type')
    if schema.get('format') == 'uuid':
        return "00000000-0000-0000-0000-000000000000"
    if schema.get('format') == 'date':
        return "2025-01-01"
    if schema.get('format') == 'date-time':
        return "2025-01-01T00:00:00Z"

    if schema_type == 'object':
        properties = schema.get('properties', {}) or {}
        required = schema.get('required', []) or []
        obj: Dict[str, Any] = {}
        for prop in required:
            if prop in properties:
                obj[prop] = generate_sample_from_schema(properties[prop])
        return obj

    if schema_type == 'array':
        items = schema.get('items', {}) or {}
        return [generate_sample_from_schema(items)]

    if schema_type == 'integer':
        return 0

    if schema_type == 'number':
        return 0

    if schema_type == 'boolean':
        return True

    return "test-value"


def generate_param_value(param: Dict[str, Any]) -> Any:
    """Generate a parameter value from examples, enums, or schema defaults."""
    schema = param.get('schema', {}) or {}
    if 'example' in param:
        return param['example']
    if 'example' in schema:
        return schema['example']
    if schema.get('enum'):
        return schema['enum'][0]
    if schema.get('format') == 'uuid':
        return "00000000-0000-0000-0000-000000000000"
    if schema.get('format') == 'date':
        return "2025-01-01"
    if schema.get('format') == 'date-time':
        return "2025-01-01T00:00:00Z"
    if schema.get('format') == 'uri':
        return "https://example.com/cert"
    if schema.get('type') in ('integer', 'number'):
        return 1
    if schema.get('type') == 'boolean':
        return True
    return "test-value"


def generate_request_data(operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate request data from operation schema or examples."""
    request_body = operation.get('requestBody', {})
    if not request_body:
        return None
    
    content = request_body.get('content', {})
    json_content = content.get('application/json', {})
    
    # Try to get example first
    if 'example' in json_content:
        return json_content['example']
    
    # Try examples
    if 'examples' in json_content:
        examples = json_content['examples']
        if examples:
            first_example = list(examples.values())[0]
            if 'value' in first_example:
                return first_example['value']
    
    # Fallback: generate minimal data from schema (recursive)
    schema = json_content.get('schema', {})
    if schema:
        return generate_sample_from_schema(schema)
    
    return None


def build_url(base_url: str, path: str, parameters: List[Dict[str, Any]]) -> str:
    """Populate path/query parameters using examples or sensible defaults."""
    path_params: Dict[str, Any] = {}
    query_params: Dict[str, Any] = {}

    for param in parameters:
        location = param.get('in')
        name = param.get('name')
        if not location or not name:
            continue

        value = generate_param_value(param)

        if location == 'path':
            path_params[name] = value
        elif location == 'query':
            query_params[name] = value

    populated_path = path
    for name, value in path_params.items():
        populated_path = populated_path.replace(f"{{{name}}}", str(value))

    if query_params:
        return f"{base_url}{populated_path}?{urlencode(query_params, doseq=True)}"
    return f"{base_url}{populated_path}"


def make_request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


def choose_accept_header(responses: Dict[str, Any]) -> str:
    """Select an Accept header based on available response content types."""
    preferred_statuses = ['200', '201', '202', 'default']
    for status in preferred_statuses:
        if status in responses:
            response_spec = responses.get(status) or {}
            content = response_spec.get('content', {}) if isinstance(response_spec, dict) else {}
            if 'application/json' in content:
                return 'application/json'
            if content:
                return next(iter(content.keys()))
    return "*/*"


def validate_response_against_schema(response_data: Any, schema: Dict[str, Any], path: str, method: str) -> List[str]:
    """
    Validate response data against schema.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Basic type checking
    schema_type = schema.get('type')
    if schema_type == 'object':
        if not isinstance(response_data, dict):
            errors.append(f"Expected object, got {type(response_data).__name__}")
            return errors
        
        # Check required properties
        required = schema.get('required', [])
        for prop in required:
            if prop not in response_data:
                errors.append(f"Missing required property: '{prop}'")
        
        # Check property types
        properties = schema.get('properties', {})
        for prop, value in response_data.items():
            if prop in properties:
                prop_schema = properties[prop]
                if value is None and prop_schema.get('nullable'):
                    continue
                prop_type = prop_schema.get('type')
                
                if prop_type == 'string' and not isinstance(value, str):
                    errors.append(f"Property '{prop}': expected string, got {type(value).__name__}")
                elif prop_type == 'integer' and not isinstance(value, int):
                    errors.append(f"Property '{prop}': expected integer, got {type(value).__name__}")
                elif prop_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Property '{prop}': expected boolean, got {type(value).__name__}")
                elif prop_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Property '{prop}': expected number, got {type(value).__name__}")
                elif prop_type == 'array' and not isinstance(value, list):
                    errors.append(f"Property '{prop}': expected array, got {type(value).__name__}")
                elif prop_type == 'object' and not isinstance(value, dict):
                    errors.append(f"Property '{prop}': expected object, got {type(value).__name__}")
    
    return errors


# Generate test parameters for primary mocks
primary_mocks = get_primary_mocks()


@pytest.mark.parametrize("mock", primary_mocks, ids=lambda m: m['id'])
def test_mock_integrity(mock):
    """
    Test that mock server serves contract-compliant responses.
    
    This is Schmidt's Phase B: Contract Integrity Check
    Validates that examples in contracts conform to their own schemas.
    
    If this test fails:
      -> Contract has invalid examples (fix contract)
    
    If this passes but provider tests fail:
      -> Implementation divergence (fix implementation)
    """
    mock_id = mock['id']
    base_url = mock['base_url']
    bundle_path = mock['bundle_path']
    
    print(f"\nTesting mock integrity for: {mock_id}")
    print(f"Bundle: {bundle_path}")
    print(f"Base URL: {base_url}")
    
    # Load bundle
    bundle = load_bundle(bundle_path)
    operations = extract_operations(bundle)
    
    print(f"Found {len(operations)} operations")
    
    if len(operations) == 0:
        pytest.skip(f"No operations found in bundle for {mock_id}")
    
    # Track results
    tested_operations = []
    failed_operations = []
    
    for op in operations:
        path = op['path']
        method = op['method']
        operation_id = op['operation_id']
        
        print(f"\n  Testing: {method} {path} ({operation_id})")
        
        # Build request
        url = build_url(base_url, path, op['parameters'])
        headers = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': '00000000-0000-0000-0000-000000000000',
            'Authorization': 'Bearer mock-token',  # For endpoints requiring auth
            'Accept': 'application/json'
        }
        header_params = {
            param['name']: generate_param_value(param)
            for param in op['parameters']
            if param.get('in') == 'header' and param.get('name')
        }
        for name, value in header_params.items():
            headers.setdefault(name, value)
        headers['Accept'] = choose_accept_header(op['responses'])
        
        # Get request data if needed
        request_data = generate_request_data(op)
        
        try:
            # Make request
            if request_data is not None:
                response = make_request_with_retry(method, url, headers=headers, json=request_data)
            else:
                response = make_request_with_retry(method, url, headers=headers)
            
            print(f"    Response: HTTP {response.status_code}")
            
            # Get expected responses from operation
            responses = op['responses']
            status_code_str = str(response.status_code)
            
            # Check if status code is allowed
            if status_code_str not in responses and 'default' not in responses:
                error_msg = f"Unexpected status code {response.status_code}. Allowed: {list(responses.keys())}"
                failed_operations.append({
                    'operation': f"{method} {path}",
                    'error': error_msg
                })
                print(f"    FAIL: {error_msg}")
                continue
            
            # Get response schema
            response_spec = responses.get(status_code_str) or responses.get('default')
            if not response_spec:
                continue
            
            content = response_spec.get('content', {})
            json_content = content.get('application/json', {})
            schema = json_content.get('schema', {})
            
            if not schema:
                # No schema to validate against
                tested_operations.append(f"{method} {path}")
                print(f"    PASS: No schema validation required")
                continue
            
            # Parse response JSON
            try:
                response_data = response.json()
            except Exception as e:
                error_msg = f"Failed to parse JSON response: {e}"
                failed_operations.append({
                    'operation': f"{method} {path}",
                    'error': error_msg
                })
                print(f"    FAIL: {error_msg}")
                continue
            
            # Validate against schema
            validation_errors = validate_response_against_schema(response_data, schema, path, method)
            
            if validation_errors:
                error_msg = "; ".join(validation_errors)
                failed_operations.append({
                    'operation': f"{method} {path}",
                    'error': error_msg
                })
                print(f"    FAIL: {error_msg}")
            else:
                tested_operations.append(f"{method} {path}")
                print(f"    PASS: Schema validation successful")
        
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            failed_operations.append({
                'operation': f"{method} {path}",
                'error': error_msg
            })
            print(f"    FAIL: {error_msg}")
    
    # Print summary
    print(f"\n  Summary for {mock_id}:")
    print(f"    Tested: {len(tested_operations)}/{len(operations)}")
    print(f"    Failed: {len(failed_operations)}")
    
    # Assert results
    if failed_operations:
        failure_report = "\n".join([
            f"    - {op['operation']}: {op['error']}"
            for op in failed_operations
        ])
        pytest.fail(
            f"\nContract integrity validation failed for {mock_id}:\n"
            f"  {len(failed_operations)} operation(s) failed:\n"
            f"{failure_report}\n\n"
            f"  This indicates contract examples are invalid against their own schemas.\n"
            f"  Action: Fix the contract examples in the source YAML files."
        )
    
    # Assert coverage
    assert len(tested_operations) > 0, f"No operations successfully tested for {mock_id}"
    print(f"\n[SUCCESS] {mock_id}: All {len(tested_operations)} operations passed integrity check")


def test_mock_servers_running():
    """
    Prerequisite test: Verify mock servers are running.
    
    If this fails, run: bash scripts/start-mocks.sh
    """
    registry = load_mock_registry()
    primary = registry['primary_mocks']
    port_mapping = registry['port_mapping']
    
    print("\nChecking if primary mocks are running...")
    
    failures = []
    for mock_id in primary:
        port = port_mapping[mock_id]
        url = f"http://localhost:{port}"
        
        try:
            response = requests.get(f"{url}/", timeout=2)
            print(f"  ✓ {mock_id} (port {port}): responding")
        except requests.exceptions.RequestException as e:
            failures.append(f"{mock_id} (port {port}): {e}")
            print(f"  ✗ {mock_id} (port {port}): not responding")
    
    if failures:
        pytest.fail(
            f"\nMock servers not running:\n" +
            "\n".join(f"  - {f}" for f in failures) +
            f"\n\nRun: bash scripts/start-mocks.sh"
        )


def test_coverage_report():
    """Generate coverage report for mock integrity tests."""
    print("\n" + "=" * 80)
    print("MOCK INTEGRITY TEST COVERAGE REPORT")
    print("=" * 80)
    
    mocks = get_primary_mocks()
    
    total_operations = 0
    for mock in mocks:
        bundle = load_bundle(mock['bundle_path'])
        operations = extract_operations(bundle)
        total_operations += len(operations)
        
        print(f"\n{mock['id']}:")
        print(f"  Port: {mock['port']}")
        print(f"  Operations: {len(operations)}")
        
        for op in operations:
            print(f"    - {op['method']} {op['path']}")
    
    print(f"\nTotal Operations (Primary Mocks): {total_operations}")
    print("=" * 80)


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v", "-s"])
