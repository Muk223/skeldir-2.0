"""
Pydantic models generated from bundled OpenAPI contracts.

These models are auto-generated from api-contracts/dist/openapi/v1/*.bundled.yaml files.
Do not edit manually. Regenerate using scripts/generate-models.sh after contract changes.
Note: Bundled artifacts are generated from source specs via scripts/contracts/bundle.sh.

Operational Gate P5: These imports MUST succeed or application cannot start.
"""

# Operational Gate P5: Hard boot-time dependency on generated models
# If models are missing, application cannot start
try:
    from .attribution import RealtimeRevenueResponse
    from .auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
    from .reconciliation import ReconciliationStatusResponse
    from .export import ExportRevenueResponse
    from .revenue import RealtimeRevenueV1Response
except ImportError as e:
    # Operational Gate P5: Hard boot-time dependency
    # If models are missing, application cannot start
    import sys
    print(f"FATAL: Required generated models are missing: {e}", file=sys.stderr)
    print("Please run: bash scripts/contracts/bundle.sh && bash scripts/generate-models.sh", file=sys.stderr)
    sys.exit(1)

# Import all other models (webhooks, etc.)
from .attribution import *
from .auth import *
from .reconciliation import *
from .export import *
from .revenue import *
from .webhooks_shopify import *
from .webhooks_stripe import *
from .webhooks_paypal import *
from .webhooks_woocommerce import *

__all__ = [
    # Attribution models
    # Auth models
    # Reconciliation models
    # Export models
    # Webhook models
    # Add other model exports as they are generated
]
