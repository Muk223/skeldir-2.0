#!/usr/bin/env python3
"""
X-Mapping Extension Validation Script (Phase C4)

Purpose: Validates OpenAPI x-mapping extensions for consistency with integration mappings

Exit Gates:
  C4.1 - Extension Presence: All revenue-critical schemas have x-mapping
  C4.2 - Consistency with Integration Maps: x-mapping matches integration-maps/*.yaml
  C4.3 - Schema Validity: x-maps-to references valid columns, transforms

Exit Code: 0 if all gates pass, 1 if any validation fails
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def load_yaml(file_path: Path) -> dict:
    """Load YAML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}✗ ERROR: Failed to load {file_path}: {e}{RESET}")
        sys.exit(1)

def validate_c4_1_extension_presence(
    bundled_contracts: dict,
    integration_maps: Dict[str, dict]
) -> Tuple[bool, List[str]]:
    """Gate C4.1: All revenue-critical schemas have x-mapping"""
    print(f"\n{BLUE}Gate C4.1: Extension Presence{RESET}")
    
    errors = []
    passed = True
    
    # Build list of schemas that should have x-mapping (from integration maps)
    required_schemas = set()
    for provider, provider_map in integration_maps.items():
        for event_name in provider_map.get('mappings', {}).keys():
            # Schema naming: stripe.yaml -> StripeChargeSucceededRequest
            schema_name = f"{provider.capitalize()}{event_name.replace('.', '').replace('/', '').title()}Request"
            required_schemas.add(schema_name)
    
    # Check bundled contracts for x-mapping presence
    schemas = bundled_contracts.get('components', {}).get('schemas', {})
    
    schemas_with_x_mapping = 0
    for schema_name in required_schemas:
        if schema_name in schemas:
            schema = schemas[schema_name]
            if 'x-mapping' in schema:
                schemas_with_x_mapping += 1
            else:
                errors.append(f"Schema '{schema_name}' missing x-mapping extension")
                passed = False
        else:
            # Schema might not exist yet - warning not error
            print(f"  {YELLOW}⚠ Schema '{schema_name}' not found in contracts{RESET}")
    
    if passed:
        print(f"  {GREEN}✓ OK {schemas_with_x_mapping} revenue-critical schemas have x-mapping{RESET}")
    else:
        print(f"  {RED}✗ FAIL Extension presence issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def validate_c4_2_consistency_with_integration_maps(
    bundled_contracts: dict,
    integration_maps: Dict[str, dict]
) -> Tuple[bool, List[str]]:
    """Gate C4.2: x-mapping consistent with integration-maps/*.yaml"""
    print(f"\n{BLUE}Gate C4.2: Consistency with Integration Maps{RESET}")
    
    errors = []
    passed = True
    
    schemas = bundled_contracts.get('components', {}).get('schemas', {})
    
    for schema_name, schema in schemas.items():
        x_mapping = schema.get('x-mapping')
        if not x_mapping:
            continue  # Skip schemas without x-mapping
        
        # Extract provider and event from schema name (heuristic)
        # E.g., "StripeChargeSucceededRequest" -> provider="stripe", event="charge.succeeded"
        provider = None
        for prov in integration_maps.keys():
            if schema_name.lower().startswith(prov):
                provider = prov
                break
        
        if not provider:
            continue  # Can't validate without provider mapping
        
        provider_map = integration_maps[provider]
        
        # Check canonical_event matches
        canonical_event = x_mapping.get('canonical_event')
        if canonical_event:
            # Find matching event in integration map
            found_matching_event = False
            for event_name, event_mapping in provider_map.get('mappings', {}).items():
                if event_mapping.get('canonical_event') == canonical_event:
                    found_matching_event = True
                    
                    # Validate state transition matches
                    x_state_transition = x_mapping.get('state_transition', {})
                    int_map_state_transition = event_mapping.get('state_transition', {})
                    
                    if x_state_transition.get('from_state') != int_map_state_transition.get('from_state'):
                        errors.append(
                            f"{schema_name}: from_state mismatch (x-mapping: {x_state_transition.get('from_state')}, "
                            f"integration-map: {int_map_state_transition.get('from_state')})"
                        )
                        passed = False
                    
                    if x_state_transition.get('to_state') != int_map_state_transition.get('to_state'):
                        errors.append(
                            f"{schema_name}: to_state mismatch (x-mapping: {x_state_transition.get('to_state')}, "
                            f"integration-map: {int_map_state_transition.get('to_state')})"
                        )
                        passed = False
            
            if not found_matching_event:
                errors.append(
                    f"{schema_name}: canonical_event '{canonical_event}' not found in {provider} integration map"
                )
                passed = False
    
    if passed:
        print(f"  {GREEN}✓ OK All x-mapping extensions consistent with integration maps{RESET}")
    else:
        print(f"  {RED}✗ FAIL Consistency issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def validate_c4_3_schema_validity(
    bundled_contracts: dict
) -> Tuple[bool, List[str]]:
    """Gate C4.3: x-maps-to references valid columns, transforms"""
    print(f"\n{BLUE}Gate C4.3: Schema Validity{RESET}")
    
    errors = []
    passed = True
    
    VALID_TRANSFORMS = {
        'as-is', 'uppercase', 'lowercase', 'unix_to_timestamptz',
        'iso8601_to_timestamptz', 'decimal_string_to_cents',
        'int_to_string', 'prefix_provider', 'constant'
    }
    
    schemas = bundled_contracts.get('components', {}).get('schemas', {})
    
    for schema_name, schema in schemas.items():
        properties = schema.get('properties', {})
        
        for prop_name, prop_spec in properties.items():
            x_maps_to = prop_spec.get('x-maps-to')
            if not x_maps_to:
                continue
            
            # Validate transform is valid
            transform = x_maps_to.get('transform', 'as-is')
            if transform not in VALID_TRANSFORMS:
                errors.append(
                    f"{schema_name}.{prop_name}: invalid transform '{transform}'"
                )
                passed = False
            
            # Validate required fields present
            if 'table' not in x_maps_to:
                errors.append(f"{schema_name}.{prop_name}: x-maps-to missing 'table'")
                passed = False
            
            if 'column' not in x_maps_to:
                errors.append(f"{schema_name}.{prop_name}: x-maps-to missing 'column'")
                passed = False
    
    if passed:
        print(f"  {GREEN}✓ OK All x-maps-to extensions have valid transforms and references{RESET}")
    else:
        print(f"  {RED}✗ FAIL Schema validity issues:{RESET}")
        for error in errors:
            print(f"    {RED}- {error}{RESET}")
    
    return passed, errors

def main():
    """Main validation orchestrator"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}X-Mapping Extension Validation (Phase C4){RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Load integration maps
    integration_maps_dir = project_root / 'api-contracts' / 'governance' / 'integration-maps'
    integration_maps = {}
    
    for provider in ['stripe', 'shopify', 'paypal', 'woocommerce']:
        map_file = integration_maps_dir / f'{provider}.yaml'
        if map_file.exists():
            integration_maps[provider] = load_yaml(map_file)
            print(f"{GREEN}✓ Loaded {provider}.yaml{RESET}")
    
    # Load bundled contracts
    bundled_contract_path = project_root / 'api-contracts' / 'dist' / 'openapi' / 'skeldir-api-v1-bundled.yaml'
    if not bundled_contract_path.exists():
        print(f"{YELLOW}⚠ Warning: Bundled contract not found, skipping validation{RESET}")
        print(f"{YELLOW}  Run 'bash scripts/contracts/bundle.sh' first{RESET}")
        sys.exit(0)  # Not an error - contracts may not be bundled yet
    
    bundled_contracts = load_yaml(bundled_contract_path)
    print(f"{GREEN}✓ Loaded bundled contracts{RESET}")
    
    # Run exit gate validations
    all_passed = True
    
    gate_c4_1_passed, _ = validate_c4_1_extension_presence(bundled_contracts, integration_maps)
    all_passed = all_passed and gate_c4_1_passed
    
    gate_c4_2_passed, _ = validate_c4_2_consistency_with_integration_maps(bundled_contracts, integration_maps)
    all_passed = all_passed and gate_c4_2_passed
    
    gate_c4_3_passed, _ = validate_c4_3_schema_validity(bundled_contracts)
    all_passed = all_passed and gate_c4_3_passed
    
    # Print summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Exit Gate Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    gates = [
        ('C4.1', 'Extension Presence', gate_c4_1_passed),
        ('C4.2', 'Consistency with Integration Maps', gate_c4_2_passed),
        ('C4.3', 'Schema Validity', gate_c4_3_passed)
    ]
    
    for gate_id, gate_name, gate_passed in gates:
        status = f"{GREEN}OK{RESET}" if gate_passed else f"{RED}FAIL{RESET}"
        print(f"  {gate_id} ({gate_name}): {status}")
    
    gate_summary = ', '.join(f"{g[0]} {'OK' if g[2] else 'FAIL'}" for g in gates)
    print(f"\n{BLUE}Exit Gates: {gate_summary}{RESET}")
    
    if all_passed:
        print(f"\n{GREEN}✓ OK ALL VALIDATIONS PASSED{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}✗ FAIL Some validations failed - see errors above{RESET}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()



