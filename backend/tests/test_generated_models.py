#!/usr/bin/env python3
"""
Unit tests for generated Pydantic models.
Validates model structure and basic functionality.
"""

import pytest
from pydantic import ValidationError


def test_realtime_revenue_response_import():
    """Test that RealtimeRevenueResponse can be imported."""
    from backend.app.schemas.attribution import RealtimeRevenueResponse
    assert RealtimeRevenueResponse is not None


def test_login_request_validation():
    """Test LoginRequest validates correctly."""
    from backend.app.schemas.auth import LoginRequest

    # Valid request
    valid_data = {"username": "test@example.com", "password": "securepass123"}
    request = LoginRequest(**valid_data)
    assert request.username == "test@example.com"


def test_model_inheritance():
    """Test that RealtimeRevenueResponse inherits from RealtimeRevenueCounter."""
    from backend.app.schemas.attribution import (
        RealtimeRevenueResponse,
        RealtimeRevenueCounter,
    )

    assert issubclass(RealtimeRevenueResponse, RealtimeRevenueCounter)


def test_webhook_acknowledgement():
    """Test webhook acknowledgement model."""
    from backend.app.schemas.webhooks_shopify import WebhookAcknowledgement

    ack = WebhookAcknowledgement(status="received", message="Webhook processed")
    assert ack.status == "received"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
