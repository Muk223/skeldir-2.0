#!/usr/bin/env python3
"""
Extract OpenAPI contract operations for evidence capture.
Phase B.2: Contract State Capture
"""
import yaml
from pathlib import Path
import datetime

contracts_dir = Path("api-contracts/dist/openapi/v1")
print("=== OpenAPI Contract Operations Map ===")
print(f"Timestamp: {datetime.datetime.now().isoformat()}\n")

for contract_file in sorted(contracts_dir.glob("*.bundled.yaml")):
    print(f"\n=== {contract_file.name} ===")
    try:
        with open(contract_file, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        if 'paths' in spec:
            for path, methods in spec['paths'].items():
                for method, operation in methods.items():
                    if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                        operation_id = operation.get('operationId', 'N/A')
                        summary = operation.get('summary', 'N/A')
                        print(f"{method.upper():6} {path:50} | operationId={operation_id}")
        else:
            print("  No paths defined")
    except Exception as e:
        print(f"  ERROR reading {contract_file.name}: {e}")

print("\n=== Summary ===")
total_operations = 0
for contract_file in sorted(contracts_dir.glob("*.bundled.yaml")):
    try:
        with open(contract_file, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        if 'paths' in spec:
            ops = sum(1 for path in spec['paths'].values() 
                     for method in path.keys() 
                     if method.lower() in ['get', 'post', 'put', 'patch', 'delete'])
            total_operations += ops
            print(f"{contract_file.name}: {ops} operations")
    except:
        pass

print(f"\nTotal operations across all contracts: {total_operations}")

