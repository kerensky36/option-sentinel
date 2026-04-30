from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.database import get_db
from src.auth.schwab_oauth import get_schwab_client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session
