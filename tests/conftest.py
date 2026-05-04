"""Shared test fixtures for the stateless Option Sentinel architecture.

No database fixtures — the app has no database.
"""
from __future__ import annotations

import base64
import json

import pytest


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Returns Authorization headers with a mock Schwab token for route tests.

    The token is base64-encoded JSON in the format expected by get_schwab_client().
    """
    token_dict = {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_type": "Bearer",
        "access_token_expiry": 9999999999,
        "refresh_token_expiry": 9999999999,
        "scope": "api",
        "expires_in": 1800,
    }
    json_str = json.dumps(token_dict)
    b64 = base64.b64encode(json_str.encode()).decode()
    return {"Authorization": f"Bearer {b64}"}
