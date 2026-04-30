import os
import asyncio
from pathlib import Path

import schwab
from schwab import auth as schwab_auth

_client: schwab.client.AsyncClient | None = None

APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")
TOKEN_PATH = Path(os.getenv("SCHWAB_TOKEN_PATH", "./schwab_token.json"))


def _build_client() -> schwab.client.AsyncClient:
    if TOKEN_PATH.exists():
        return schwab_auth.client_from_token_file(
            token_path=str(TOKEN_PATH),
            api_key=APP_KEY,
            app_secret=APP_SECRET,
            asyncio=True,
        )
    return schwab_auth.client_from_manual_flow(
        api_key=APP_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=str(TOKEN_PATH),
        asyncio=True,
    )


async def get_schwab_client() -> schwab.client.AsyncClient:
    global _client
    if _client is None:
        loop = asyncio.get_event_loop()
        _client = await loop.run_in_executor(None, _build_client)
    return _client


def reset_client() -> None:
    global _client
    _client = None
