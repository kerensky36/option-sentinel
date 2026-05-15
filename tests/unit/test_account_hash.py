"""Unit tests for account_hash resolution in schwab_client._fetch_positions."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_ACCOUNTS = [
    {"accountNumber": "11111111", "hashValue": "hash-one"},
    {"accountNumber": "22222222", "hashValue": "hash-two"},
]


@pytest.mark.asyncio
class TestFetchPositionsAccountHash:
    async def test_uses_first_account_when_hash_is_none(self):
        """_fetch_positions(client, account_hash=None) uses accounts[0]["hashValue"]."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"securitiesAccount": {"positions": []}}
        mock_client.get_account = AsyncMock(return_value=mock_resp)
        mock_client.Account.Fields.POSITIONS = "positions"

        with patch(
            "src.auth.account_resolver.list_accounts",
            new_callable=AsyncMock,
            return_value=_ACCOUNTS,
        ):
            from src.services.schwab_client import _fetch_positions
            await _fetch_positions(mock_client, account_hash=None)

        mock_client.get_account.assert_called_once_with(
            "hash-one", fields=[mock_client.Account.Fields.POSITIONS]
        )

    async def test_uses_provided_hash_when_valid(self):
        """_fetch_positions(client, account_hash='hash-two') uses that hash directly."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"securitiesAccount": {"positions": []}}
        mock_client.get_account = AsyncMock(return_value=mock_resp)
        mock_client.Account.Fields.POSITIONS = "positions"

        with patch(
            "src.auth.account_resolver.list_accounts",
            new_callable=AsyncMock,
            return_value=_ACCOUNTS,
        ):
            from src.services.schwab_client import _fetch_positions
            await _fetch_positions(mock_client, account_hash="hash-two")

        mock_client.get_account.assert_called_once_with(
            "hash-two", fields=[mock_client.Account.Fields.POSITIONS]
        )

    async def test_raises_value_error_for_unknown_hash(self):
        """_fetch_positions raises ValueError when account_hash is not in account list."""
        mock_client = MagicMock()

        with patch(
            "src.auth.account_resolver.list_accounts",
            new_callable=AsyncMock,
            return_value=_ACCOUNTS,
        ):
            from src.services.schwab_client import _fetch_positions
            with pytest.raises(ValueError, match="not found"):
                await _fetch_positions(mock_client, account_hash="unknown-hash-xyz")

    async def test_returns_empty_list_when_no_accounts(self):
        """_fetch_positions returns [] when account list is empty (no accounts on token)."""
        mock_client = MagicMock()

        with patch(
            "src.auth.account_resolver.list_accounts",
            new_callable=AsyncMock,
            return_value=[],
        ):
            from src.services.schwab_client import _fetch_positions
            result = await _fetch_positions(mock_client, account_hash=None)

        assert result == []
