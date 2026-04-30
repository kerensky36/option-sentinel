import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import AuthToken

RE_AUTH_WARN_HOURS = 24

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("SECRET_KEY", "")
        if not key:
            raise RuntimeError("SECRET_KEY env var is not set")
        _fernet = Fernet(key.encode())
    return _fernet


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


async def get_auth_token(session: AsyncSession) -> AuthToken | None:
    result = await session.execute(select(AuthToken).where(AuthToken.id == 1))
    return result.scalar_one_or_none()


async def save_auth_token(
    session: AsyncSession,
    access_token: str,
    access_expiry: datetime,
    refresh_token: str,
    refresh_expiry: datetime,
) -> AuthToken:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    re_auth_required = refresh_expiry < now + timedelta(hours=RE_AUTH_WARN_HOURS)

    token = await get_auth_token(session)
    if token is None:
        token = AuthToken(id=1)
        session.add(token)

    token.access_token = _encrypt(access_token)
    token.access_expiry = access_expiry
    token.refresh_token = _encrypt(refresh_token)
    token.refresh_expiry = refresh_expiry
    token.re_auth_required = re_auth_required
    token.last_refreshed = now

    await session.commit()
    await session.refresh(token)
    return token


async def get_decrypted_tokens(session: AsyncSession) -> tuple[str, str] | None:
    token = await get_auth_token(session)
    if token is None:
        return None
    return _decrypt(token.access_token), _decrypt(token.refresh_token)


async def check_and_update_re_auth(session: AsyncSession) -> bool:
    token = await get_auth_token(session)
    if token is None:
        return False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    needs_reauth = token.refresh_expiry < now + timedelta(hours=RE_AUTH_WARN_HOURS)
    if needs_reauth != token.re_auth_required:
        token.re_auth_required = needs_reauth
        await session.commit()
    return needs_reauth
