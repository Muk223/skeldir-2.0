"""
PII Stripping Middleware - Phase G: Active Privacy Defense

Implements runtime PII filtering as first layer of defense-in-depth.
Works in coordination with database triggers (second layer).

Defense-in-Depth Strategy:
- Layer 1 (Runtime): This middleware strips PII before application logic
- Layer 2 (Database): Triggers block PII if middleware is bypassed
- Layer 3 (Audit): Periodic scanning detects residual contamination

PII Keys Detected:
- email: Email addresses
- phone: Phone numbers
- address: Physical addresses
- ip: IP addresses
- ssn: Social security numbers
- credit_card: Credit card numbers
- passport: Passport numbers

Behavior:
- Recursively traverses incoming JSON payloads
- Replaces values of PII keys with "[REDACTED]"
- Logs redaction events for monitoring
- Allows request to proceed (does not block)
"""

import json
import logging
from typing import Any, Dict, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# PII keys to detect and redact
PII_KEYS: Set[str] = {
    "email",
    "phone",
    "address",
    "ip",
    "ssn",
    "credit_card",
    "passport",
    "billing_address",
    "shipping_address",
    "customer_email",
    "customer_phone",
}


def redact_pii_recursive(data: Any, path: str = "root") -> tuple[Any, list[str]]:
    """
    Recursively traverse data structure and redact PII values.
    
    Args:
        data: Data structure to traverse (dict, list, or scalar)
        path: Current path in data structure (for logging)
    
    Returns:
        Tuple of (redacted_data, redacted_keys_list)
    """
    redacted_keys = []
    
    if isinstance(data, dict):
        redacted_dict = {}
        for key, value in data.items():
            current_path = f"{path}.{key}"
            
            # Check if key is PII
            if key.lower() in PII_KEYS:
                redacted_dict[key] = "[REDACTED]"
                redacted_keys.append(current_path)
            else:
                # Recursively process nested structures
                redacted_value, nested_redactions = redact_pii_recursive(value, current_path)
                redacted_dict[key] = redacted_value
                redacted_keys.extend(nested_redactions)
        
        return redacted_dict, redacted_keys
    
    elif isinstance(data, list):
        redacted_list = []
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            redacted_item, nested_redactions = redact_pii_recursive(item, current_path)
            redacted_list.append(redacted_item)
            redacted_keys.extend(nested_redactions)
        
        return redacted_list, redacted_keys
    
    else:
        # Scalar value - return as-is
        return data, redacted_keys


class PIIStrippingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that strips PII from incoming request payloads.
    
    Executes before Pydantic validation to ensure PII never reaches
    application logic or database layer.
    
    Usage:
        app.add_middleware(PIIStrippingMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and strip PII from JSON payloads.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response from downstream handler
        """
        # Only process POST/PUT/PATCH requests with JSON content
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    # Read request body
                    body = await request.body()
                    
                    if body:
                        # Parse JSON
                        try:
                            payload = json.loads(body)
                        except json.JSONDecodeError:
                            # Invalid JSON - let it pass through for proper error handling
                            logger.warning("Invalid JSON in request body, skipping PII redaction")
                            return await call_next(request)
                        
                        # Redact PII
                        redacted_payload, redacted_keys = redact_pii_recursive(payload)
                        
                        # Log redaction events
                        if redacted_keys:
                            logger.info(
                                f"PII redacted from request",
                                extra={
                                    "event_type": "pii_redaction",
                                    "path": request.url.path,
                                    "method": request.method,
                                    "redacted_keys": redacted_keys,
                                    "redaction_count": len(redacted_keys)
                                }
                            )
                        
                        # Replace request body with redacted version
                        redacted_body = json.dumps(redacted_payload).encode('utf-8')
                        
                        # Create new request with redacted body
                        async def receive():
                            return {"type": "http.request", "body": redacted_body}
                        
                        request._receive = receive
                
                except Exception as e:
                    logger.error(
                        f"Error during PII redaction: {e}",
                        extra={
                            "event_type": "pii_redaction_error",
                            "path": request.url.path,
                            "method": request.method,
                            "error": str(e)
                        }
                    )
                    # Continue processing request despite error
        
        # Continue to next middleware/handler
        response = await call_next(request)
        return response

