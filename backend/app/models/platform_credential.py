"""
PlatformCredential ORM model.

Stores encrypted platform access/refresh tokens per tenant/platform connection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import BYTEA, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class PlatformCredential(Base, TenantMixin):
    __tablename__ = "platform_credentials"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )
    platform_connection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_access_token: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    encrypted_refresh_token: Mapped[Optional[bytes]] = mapped_column(BYTEA, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "platform",
            "platform_connection_id",
            name="uq_platform_credentials_tenant_platform_connection",
        ),
    )
