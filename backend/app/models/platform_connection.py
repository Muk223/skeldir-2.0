"""
PlatformConnection ORM model.

Represents tenant-scoped bindings between a tenant and a platform account.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class PlatformConnection(Base, TenantMixin):
    __tablename__ = "platform_connections"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    connection_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

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
            "platform_account_id",
            name="uq_platform_connections_tenant_platform_account",
        ),
        CheckConstraint(
            "status IN ('pending', 'active', 'disabled')",
            name="ck_platform_connections_status_valid",
        ),
    )
