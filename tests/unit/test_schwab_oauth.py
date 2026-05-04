"""Unit tests for Schwab OAuth helpers."""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBuildAuthUrl:
    def test_returns_url_and_state(self):
        """build_auth_url() returns a non-empty URL string and a non-empty state."""
        with patch("src.auth.schwab_oauth.schwab_auth") as mock_auth:
            # Mock the OAuth2Client chain
            mock_client = MagicMock()
            mock_client.create_authorization_url.return_value = (
                "https://api.schwabapi.com/v1/oauth/authorize?client_id=key&state=teststate123",
                "teststate123",
            )
            mock_auth.oauth.OAuth2Client.return_value = mock_client

            from src.auth.schwab_oauth import build_auth_url
            url, state = build_auth_url()

        assert isinstance(url, str)
        assert url.startswith("https://")
        assert isinstance(state, str)
        assert len(state) > 0

    def test_state_is_unique(self):
        """Each call to build_auth_url() returns a different state."""
        with patch("src.auth.schwab_oauth.schwab_auth") as mock_auth:
            mock_client = MagicMock()
            call_count = [0]

            def make_url(*args, **kwargs):
                call_count[0] += 1
                state = f"state-{call_count[0]}"
                return f"https://schwab.example.com?state={state}", state

            mock_client.create_authorization_url.side_effect = make_url
            mock_auth.oauth.OAuth2Client.return_value = mock_client

            from src.auth.schwab_oauth import build_auth_url
            _, state1 = build_auth_url()
            _, state2 = build_auth_url()

        assert state1 != state2


class TestExchangeCodeForToken:
    @pytest.mark.asyncio
    async def test_returns_token_dict_on_success(self):
        """exchange_code_for_token() returns a token dict when Schwab responds 200."""
        import httpx

        mock_response_body = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 1800,
            "refresh_token_expires_in": 604800,
            "scope": "api",
        }

        with patch("httpx.AsyncClient") as mock_http_cls:
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__.return_value = mock_http
            mock_http_cls.return_value.__aexit__.return_value = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response_body
            mock_http.post.return_value = mock_resp

            from src.auth.schwab_oauth import exchange_code_for_token

            received_url = "https://127.0.0.1?code=abc123&state=mystate"
            token = await exchange_code_for_token(received_url, "mystate")

        assert token["access_token"] == "test-access-token"
        assert token["refresh_token"] == "test-refresh-token"
        assert "access_token_expiry" in token
        assert "refresh_token_expiry" in token

    @pytest.mark.asyncio
    async def test_raises_on_state_mismatch(self):
        """exchange_code_for_token() raises ValueError when state doesn't match."""
        from src.auth.schwab_oauth import exchange_code_for_token

        received_url = "https://127.0.0.1?code=abc123&state=wrong-state"
        with pytest.raises(ValueError, match="state mismatch"):
            await exchange_code_for_token(received_url, "expected-state")

    @pytest.mark.asyncio
    async def test_raises_on_missing_code(self):
        """exchange_code_for_token() raises ValueError when no code param."""
        from src.auth.schwab_oauth import exchange_code_for_token

        received_url = "https://127.0.0.1?state=mystate"
        with pytest.raises(ValueError, match="No 'code'"):
            await exchange_code_for_token(received_url, "mystate")

    @pytest.mark.asyncio
    async def test_raises_on_oauth_error_param(self):
        """exchange_code_for_token() raises ValueError when Schwab returns error param."""
        from src.auth.schwab_oauth import exchange_code_for_token

        received_url = "https://127.0.0.1?error=access_denied&error_description=User+denied&state=mystate"
        with pytest.raises(ValueError, match="OAuth error"):
            await exchange_code_for_token(received_url, "mystate")

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        """exchange_code_for_token() raises ValueError on non-200 response from Schwab."""
        with patch("httpx.AsyncClient") as mock_http_cls:
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__.return_value = mock_http
            mock_http_cls.return_value.__aexit__.return_value = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "Bad Request"
            mock_http.post.return_value = mock_resp

            from src.auth.schwab_oauth import exchange_code_for_token

            received_url = "https://127.0.0.1?code=abc&state=mystate"
            with pytest.raises(ValueError, match="Token exchange failed"):
                await exchange_code_for_token(received_url, "mystate")


class TestRequireAuth:
    @pytest.mark.asyncio
    async def test_raises_401_when_no_authorization_header(self):
        """require_auth raises HTTP 401 when Authorization header is absent."""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from fastapi import FastAPI, Depends
        from src.api.deps import require_auth

        test_app = FastAPI()

        @test_app.get("/protected")
        async def protected(auth=Depends(require_auth)):
            return {"ok": True}

        client = TestClient(test_app, raise_server_exceptions=False)
        resp = client.get("/protected")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_passes_with_bearer_header(self):
        """require_auth does not raise when Authorization: Bearer header present."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI, Depends
        from src.api.deps import require_auth

        test_app = FastAPI()

        @test_app.get("/protected")
        async def protected(auth=Depends(require_auth)):
            return {"ok": True}

        client = TestClient(test_app)
        resp = client.get("/protected", headers={"Authorization": "Bearer sometoken"})
        assert resp.status_code == 200
