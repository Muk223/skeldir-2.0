#!/usr/bin/env python3
"""
FastAPI Route Introspection - Phase CF1 (R-Graph Generation)

This script introspects the FastAPI application to generate a canonical, machine-readable
graph of implementation routes (R-Graph).

The R-Graph is used by check_static_conformance.py to validate bidirectional alignment
between implementation and OpenAPI contracts.

Output: tmp/r_graph.json - Deterministically sorted list of implementation routes

Exit Gates:
- Running twice produces byte-identical output (deterministic)
- All in-scope routes captured exactly once
- Output includes: method, path, operationId, request/response models
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
import inspect

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


def is_in_scope(path: str, config: Dict) -> bool:
    """Check if route path is in-scope for contract enforcement."""
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


def extract_model_name(model) -> str:
    """Extract model name from type annotation or model class."""
    if model is None:
        return None
    
    if hasattr(model, '__name__'):
        return model.__name__
    elif hasattr(model, '__origin__'):
        # Handle generics like Optional[Model]
        if hasattr(model, '__args__') and model.__args__:
            return extract_model_name(model.__args__[0])
    
    return str(model)


def extract_path_params(path: str) -> List[str]:
    """Extract path parameter names from path template."""
    import re
    # FastAPI uses {param_name} format
    return re.findall(r'\{([^}]+)\}', path)


def extract_query_params(endpoint_func) -> List[Dict[str, Any]]:
    """Extract query parameter names from endpoint function signature."""
    query_params = []
    
    if not endpoint_func:
        return query_params
    
    try:
        sig = inspect.signature(endpoint_func)
        for param_name, param in sig.parameters.items():
            # Skip special parameters
            if param_name in ('request', 'self', 'cls'):
                continue
            
            # Check if it's a query parameter (not in path, not in body, not a header)
            # This is a simplified check - production would inspect fastapi.params
            annotation_str = str(param.annotation)
            if 'Header' not in annotation_str and 'Body' not in annotation_str:
                # Check if not a path param by looking at default
                if param.default is not inspect.Parameter.empty or 'Query' in annotation_str:
                    query_params.append({
                        'name': param_name,
                        'required': param.default is inspect.Parameter.empty
                    })
    except Exception as e:
        print(f"Warning: Could not extract query params: {e}", file=sys.stderr)
    
    return query_params


def dump_routes():
    """
    Introspect FastAPI app and generate R-Graph.
    
    Exit code 0: R-Graph generated successfully
    Exit code 1: App cannot be loaded or error occurred
    """
    config = load_scope_config()
    
    try:
        # Import FastAPI app
        from app.main import app
    except ImportError as e:
        print(f"ERROR: Cannot import FastAPI app: {e}", file=sys.stderr)
        print("Please ensure backend/app/main.py exists and app is defined", file=sys.stderr)
        sys.exit(1)
    
    routes = []
    
    for route in app.routes:
        # Skip non-route objects (middleware, mounts, etc.)
        if not hasattr(route, 'methods') or not hasattr(route, 'path'):
            continue
        
        path = route.path
        
        # Filter by scope
        if not is_in_scope(path, config):
            continue
        
        methods = route.methods or {'GET'}
        
        for method in methods:
            if method in ('HEAD', 'OPTIONS'):  # Skip auto-generated methods
                continue
            
            # Extract route metadata
            route_data = {
                'method': method,
                'path': path,
                'operation_id': getattr(route, 'operation_id', None) or route.name,
                'name': route.name,
                'path_params': extract_path_params(path),
                'tags': list(route.tags) if hasattr(route, 'tags') and route.tags else []
            }
            
            # Extract request model
            if hasattr(route, 'body_field') and route.body_field:
                route_data['request_model'] = extract_model_name(route.body_field.type_)
            else:
                route_data['request_model'] = None
            
            # Extract response model
            if hasattr(route, 'response_model') and route.response_model:
                route_data['response_model'] = extract_model_name(route.response_model)
            else:
                route_data['response_model'] = None
            
            # Extract query parameters
            if hasattr(route, 'endpoint'):
                route_data['query_params'] = extract_query_params(route.endpoint)
            else:
                route_data['query_params'] = []
            
            routes.append(route_data)
    
    # Sort deterministically by (path, method)
    routes.sort(key=lambda r: (r['path'], r['method']))
    
    # Create output directory
    output_dir = Path(__file__).parent.parent.parent / "tmp"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "r_graph.json"
    
    # Write R-Graph
    with open(output_path, 'w') as f:
        json.dump({
            'routes': routes,
            'metadata': {
                'total_routes': len(routes),
                'generator': 'dump_routes.py',
                'source': 'FastAPI app introspection'
            }
        }, f, indent=2, sort_keys=True)
    
    print(f"✓ Generated R-Graph: {output_path}")
    print(f"  Total in-scope routes: {len(routes)}")
    
    # Print summary by path
    for route in routes:
        print(f"    {route['method']:6s} {route['path']}")
    
    return 0


if __name__ == '__main__':
    sys.exit(dump_routes())



