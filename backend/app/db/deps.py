from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session
from app.security.auth import AuthContext, get_auth_context


async def get_db_session(
    request: Request,
    auth_context: AuthContext = Depends(get_auth_context),
) -> AsyncGenerator[AsyncSession, None]:
    async with db_session.get_session(auth_context.tenant_id) as session:
        request.state.db_session = session
        yield session
