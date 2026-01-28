"""
Service layer for platform connections.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_connection import PlatformConnection


class UnsupportedPlatformError(ValueError):
    pass


class PlatformConnectionNotFoundError(RuntimeError):
    pass


class PlatformConnectionService:
    @staticmethod
    async def upsert_connection(
        session: AsyncSession,
        *,
        tenant_id: UUID,
        platform: str,
        platform_account_id: str,
        status: str,
        metadata: Optional[dict],
    ) -> dict:
        stmt = insert(PlatformConnection).values(
            tenant_id=tenant_id,
            platform=platform,
            platform_account_id=platform_account_id,
            status=status,
            connection_metadata=metadata,
            created_at=func.now(),
            updated_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "platform", "platform_account_id"],
            set_={
                "status": status,
                "connection_metadata": metadata,
                "updated_at": func.now(),
            },
        ).returning(
            PlatformConnection.id,
            PlatformConnection.tenant_id,
            PlatformConnection.platform,
            PlatformConnection.platform_account_id,
            PlatformConnection.status,
            PlatformConnection.created_at,
            PlatformConnection.updated_at,
        )
        result = await session.execute(stmt)
        row = result.mappings().first()
        payload = dict(row)
        if "id" in payload:
            payload["id"] = str(payload["id"])
        if "tenant_id" in payload:
            payload["tenant_id"] = str(payload["tenant_id"])
        return payload

    @staticmethod
    async def get_connection(
        session: AsyncSession,
        *,
        tenant_id: UUID,
        platform: str,
        platform_account_id: Optional[str],
    ) -> dict:
        query = select(PlatformConnection).where(
            PlatformConnection.tenant_id == tenant_id,
            PlatformConnection.platform == platform,
        )
        if platform_account_id:
            query = query.where(
                PlatformConnection.platform_account_id == platform_account_id
            )
        query = query.order_by(PlatformConnection.updated_at.desc()).limit(1)
        result = await session.execute(query)
        connection = result.scalars().first()
        if not connection:
            raise PlatformConnectionNotFoundError()
        return {
            "id": str(connection.id),
            "tenant_id": str(connection.tenant_id),
            "platform": connection.platform,
            "platform_account_id": connection.platform_account_id,
            "status": connection.status,
            "metadata": connection.connection_metadata,
            "created_at": connection.created_at,
            "updated_at": connection.updated_at,
        }
