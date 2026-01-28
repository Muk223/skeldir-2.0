"""
Service layer for platform credentials (encrypted tokens).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_connection import PlatformConnection
from app.models.platform_credential import PlatformCredential
from app.services.platform_connections import PlatformConnectionNotFoundError


class PlatformCredentialExpiredError(RuntimeError):
    pass


class PlatformCredentialNotFoundError(RuntimeError):
    pass


class PlatformCredentialStore:
    @staticmethod
    async def upsert_tokens(
        session: AsyncSession,
        *,
        tenant_id: UUID,
        platform: str,
        platform_account_id: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        scope: Optional[str],
        token_type: Optional[str],
        key_id: str,
        encryption_key: str,
    ) -> dict:
        connection_query = select(PlatformConnection.id).where(
            PlatformConnection.tenant_id == tenant_id,
            PlatformConnection.platform == platform,
            PlatformConnection.platform_account_id == platform_account_id,
        )
        connection_result = await session.execute(connection_query)
        connection_id = connection_result.scalar_one_or_none()
        if not connection_id:
            raise PlatformConnectionNotFoundError()

        encrypted_access = func.pgp_sym_encrypt(access_token, encryption_key)
        encrypted_refresh = (
            func.pgp_sym_encrypt(refresh_token, encryption_key)
            if refresh_token
            else None
        )

        stmt = insert(PlatformCredential).values(
            tenant_id=tenant_id,
            platform_connection_id=connection_id,
            platform=platform,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            expires_at=expires_at,
            scope=scope,
            token_type=token_type,
            key_id=key_id,
            created_at=func.now(),
            updated_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "platform", "platform_connection_id"],
            set_={
                "encrypted_access_token": encrypted_access,
                "encrypted_refresh_token": encrypted_refresh,
                "expires_at": expires_at,
                "scope": scope,
                "token_type": token_type,
                "key_id": key_id,
                "updated_at": func.now(),
            },
        ).returning(
            PlatformCredential.id,
            PlatformCredential.expires_at,
            PlatformCredential.updated_at,
        )
        result = await session.execute(stmt)
        row = result.mappings().first()
        return dict(row)

    @staticmethod
    async def get_valid_token(
        session: AsyncSession,
        *,
        tenant_id: UUID,
        platform: str,
        platform_account_id: str,
        encryption_key: str,
    ) -> dict:
        query = (
            select(
                PlatformCredential.expires_at,
                PlatformCredential.updated_at,
                func.pgp_sym_decrypt(
                    PlatformCredential.encrypted_access_token, encryption_key
                ).label("access_token"),
            )
            .join(
                PlatformConnection,
                PlatformConnection.id == PlatformCredential.platform_connection_id,
            )
            .where(
                PlatformCredential.tenant_id == tenant_id,
                PlatformCredential.platform == platform,
                PlatformConnection.platform_account_id == platform_account_id,
            )
            .order_by(PlatformCredential.updated_at.desc())
            .limit(1)
        )
        result = await session.execute(query)
        row = result.mappings().first()
        if not row:
            raise PlatformCredentialNotFoundError()

        expires_at = row.get("expires_at")
        if expires_at and expires_at <= datetime.now(timezone.utc):
            raise PlatformCredentialExpiredError()

        return {
            "access_token": row["access_token"],
            "expires_at": expires_at,
            "updated_at": row["updated_at"],
        }
