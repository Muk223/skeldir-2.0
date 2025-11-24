#!/usr/bin/env python3
"""
Extract FastAPI routes for evidence capture.
Phase B.2: Contract State Capture
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from app.main import app
    
    print("=== FastAPI Route Map ===")
    print(f"Timestamp: {__import__('datetime').datetime.now().isoformat()}")
    print("\nRoutes:\n")
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ','.join(route.methods - {'HEAD', 'OPTIONS'})
            operation_id = getattr(route, 'operation_id', 'N/A')
            name = getattr(route, 'name', 'N/A')
            print(f"{methods:10} {route.path:50} | operation_id={operation_id} | name={name}")
    
    print(f"\nTotal routes: {len([r for r in app.routes if hasattr(r, 'methods')])}")
    
except Exception as e:
    print(f"ERROR: Failed to load FastAPI app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

