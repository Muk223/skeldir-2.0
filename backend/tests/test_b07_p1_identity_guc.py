from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from starlette.requests import Request

from app.db.deps import get_db_session
from app.db.session import get_session
from app.security.auth import AuthContext


@pytest.mark.asyncio
async def test_api_db_session_sets_user_and_tenant_guc():
    tenant_id = uuid4()
    user_id = uuid4()
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    auth_context = AuthContext(
        tenant_id=tenant_id,
        user_id=user_id,
        subject=None,
        issuer=None,
        audience=None,
        claims={},
    )

    async for session in get_db_session(request, auth_context):
        tenant = await session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        user = await session.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        )
        assert tenant.scalar() == str(tenant_id)
        assert user.scalar() == str(user_id)


@pytest.mark.asyncio
async def test_worker_session_sets_user_and_tenant_guc():
    tenant_id = uuid4()
    user_id = uuid4()
    async with get_session(tenant_id=tenant_id, user_id=user_id) as session:
        tenant = await session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        user = await session.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        )
        assert tenant.scalar() == str(tenant_id)
        assert user.scalar() == str(user_id)
