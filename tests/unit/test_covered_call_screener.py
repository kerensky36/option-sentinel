"""Unit tests for covered call screener lot-size filter (007).

Constitution Principle IV: these tests are written FIRST and must FAIL (RED)
before T002/T003 implement the fix.

The lot-size rule: only positions where shares > 0 and shares % 100 == 0
are eligible for a covered call. contracts = shares // 100.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_ENV_DEFAULTS = {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


def _make_client(accounts=None):
    client = MagicMock()
    client.Account = MagicMock()
    client.Account.Fields = MagicMock()
    client.Account.Fields.POSITIONS = "positions"
    client.Options = MagicMock()
    client.Options.ContractType = MagicMock()
    client.Options.ContractType.CALL = "CALL"
    client.Options.Type = MagicMock()
    client.Options.Type.STANDARD = "STANDARD"
    return client


def _make_position(ticker: str, shares: int) -> dict:
    return {
        "ticker": ticker,
        "shares": shares,
        "price": 100.0,
        "volatility": 0.3,
        "days_to_earnings": None,
    }


async def _run_with_positions(positions: list[dict]) -> list:
    """Helper: run screener with mocked positions list and no open calls."""
    from src.services.covered_call_screener import run_screener

    client = _make_client()

    with (
        patch(
            "src.services.covered_call_screener._fetch_stock_positions",
            new=AsyncMock(return_value=positions),
        ),
        patch(
            "src.services.covered_call_screener._fetch_open_calls",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.covered_call_screener._fetch_call_chain",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.auth.account_resolver.list_accounts",
            new=AsyncMock(return_value=[{"hashValue": "abc123"}]),
        ),
    ):
        return await run_screener(client=client, account_hash="abc123")


class TestLotSizeFilter:
    async def test_100_shares_eligible_1_contract(self):
        """Position with exactly 100 shares appears with 1 contract."""
        results = await _run_with_positions([_make_position("AAPL", 100)])
        assert len(results) == 1
        assert results[0].ticker == "AAPL"
        assert results[0].contracts == 1

    async def test_200_shares_eligible_2_contracts(self):
        """Position with 200 shares appears with 2 contracts."""
        results = await _run_with_positions([_make_position("MSFT", 200)])
        assert len(results) == 1
        assert results[0].contracts == 2

    async def test_300_shares_eligible_3_contracts(self):
        """Position with 300 shares appears with 3 contracts."""
        results = await _run_with_positions([_make_position("GOOG", 300)])
        assert len(results) == 1
        assert results[0].contracts == 3

    async def test_50_shares_filtered_out(self):
        """Position with 50 shares (not a multiple of 100) is excluded."""
        results = await _run_with_positions([_make_position("TSLA", 50)])
        assert results == []

    async def test_150_shares_filtered_out(self):
        """Position with 150 shares (not a multiple of 100) is excluded."""
        results = await _run_with_positions([_make_position("NVDA", 150)])
        assert results == []

    async def test_0_shares_filtered_out(self):
        """Position with 0 shares is excluded."""
        results = await _run_with_positions([_make_position("AMD", 0)])
        assert results == []

    async def test_negative_shares_filtered_out(self):
        """Position with negative shares (short) is excluded."""
        results = await _run_with_positions([_make_position("SPY", -100)])
        assert results == []

    async def test_mixed_portfolio_only_eligible_appear(self):
        """Only lot-sized positions appear; ineligible ones are silently dropped."""
        positions = [
            _make_position("AAPL", 100),   # eligible — 1 contract
            _make_position("TSLA", 50),    # filtered
            _make_position("MSFT", 200),   # eligible — 2 contracts
            _make_position("NVDA", 150),   # filtered
            _make_position("GOOG", 300),   # eligible — 3 contracts
        ]
        results = await _run_with_positions(positions)
        tickers = {r.ticker for r in results}
        assert tickers == {"AAPL", "MSFT", "GOOG"}
        assert all(r.ticker not in {"TSLA", "NVDA"} for r in results)

    async def test_contracts_equals_shares_divided_by_100(self):
        """contracts field is always shares // 100, no rounding up."""
        results = await _run_with_positions([_make_position("XYZ", 500)])
        assert results[0].contracts == 5

    async def test_all_ineligible_returns_empty_list(self):
        """When all positions fail the lot-size gate, screener returns empty list."""
        positions = [
            _make_position("A", 75),
            _make_position("B", 25),
            _make_position("C", 33),
        ]
        results = await _run_with_positions(positions)
        assert results == []


class TestRiskToleranceCandidates:
    """Feature 013: wide DTE fetch window and candidates field on ScreenerResultView."""

    async def test_fetch_call_chain_uses_wide_dte_window(self):
        """_fetch_call_chain must call get_option_chain with from_date ≤ today+7 and to_date ≥ today+55."""
        from datetime import date, timedelta
        from unittest.mock import AsyncMock, MagicMock
        from src.services.covered_call_screener import _fetch_call_chain

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"callExpDateMap": {}}
        client.get_option_chain = AsyncMock(return_value=mock_resp)

        await _fetch_call_chain(client, "AAPL")

        call_kwargs = client.get_option_chain.call_args.kwargs
        today = date.today()
        assert call_kwargs["from_date"] <= today + timedelta(days=7), (
            f"from_date {call_kwargs['from_date']} must be ≤ today+7 ({today + timedelta(days=7)})"
        )
        assert call_kwargs["to_date"] >= today + timedelta(days=55), (
            f"to_date {call_kwargs['to_date']} must be ≥ today+55 ({today + timedelta(days=55)})"
        )

    async def test_screener_result_includes_candidates(self):
        """Each ScreenerResultView must have a non-empty candidates list when liquid options exist."""
        from src.services.covered_call_screener import run_screener

        client = _make_client()
        chain_options = [
            {"dte": 35, "strike": 150.0, "expiry": "2026-06-20", "delta": 0.25, "bid": 1.50, "open_interest": 200},
            {"dte": 20, "strike": 145.0, "expiry": "2026-06-06", "delta": 0.30, "bid": 1.80, "open_interest": 150},
        ]

        with (
            patch("src.services.covered_call_screener._fetch_stock_positions",
                  new=AsyncMock(return_value=[_make_position("AAPL", 100)])),
            patch("src.services.covered_call_screener._fetch_open_calls",
                  new=AsyncMock(return_value=[])),
            patch("src.services.covered_call_screener._fetch_call_chain",
                  new=AsyncMock(return_value=chain_options)),
            patch("src.auth.account_resolver.list_accounts",
                  new=AsyncMock(return_value=[{"hashValue": "abc123"}])),
        ):
            results = await run_screener(client=client, account_hash="abc123")

        assert len(results) == 1
        assert hasattr(results[0], "candidates"), "ScreenerResultView must have a 'candidates' field"
        assert len(results[0].candidates) > 0, "candidates list must not be empty when liquid options exist"

    async def test_candidates_are_liquid_only(self):
        """Options with bid < 0.05 or OI < 100 must not appear in candidates."""
        from src.services.covered_call_screener import run_screener

        client = _make_client()
        chain_options = [
            {"dte": 35, "strike": 150.0, "expiry": "2026-06-20", "delta": 0.25, "bid": 1.50, "open_interest": 200},
            {"dte": 35, "strike": 155.0, "expiry": "2026-06-20", "delta": 0.20, "bid": 0.03, "open_interest": 200},
            {"dte": 35, "strike": 160.0, "expiry": "2026-06-20", "delta": 0.15, "bid": 1.00, "open_interest": 50},
        ]

        with (
            patch("src.services.covered_call_screener._fetch_stock_positions",
                  new=AsyncMock(return_value=[_make_position("AAPL", 100)])),
            patch("src.services.covered_call_screener._fetch_open_calls",
                  new=AsyncMock(return_value=[])),
            patch("src.services.covered_call_screener._fetch_call_chain",
                  new=AsyncMock(return_value=chain_options)),
            patch("src.auth.account_resolver.list_accounts",
                  new=AsyncMock(return_value=[{"hashValue": "abc123"}])),
        ):
            results = await run_screener(client=client, account_hash="abc123")

        candidates = results[0].candidates
        strikes = {c["strike"] for c in candidates}
        assert 155.0 not in strikes, "Option with bid=0.03 must not be in candidates"
        assert 160.0 not in strikes, "Option with OI=50 must not be in candidates"
        assert 150.0 in strikes, "Liquid option (bid=1.50, OI=200) must appear in candidates"

    async def test_balanced_score_matches_current_output(self):
        """Balanced profile composite_score must match _compute_composite_score (regression guard)."""
        from src.services.covered_call_screener import (
            run_screener, _compute_composite_score, _annualised_yield, _vol_score
        )

        client = _make_client()
        chain_options = [
            {"dte": 35, "strike": 150.0, "expiry": "2026-06-20", "delta": 0.25, "bid": 1.50,
             "open_interest": 200, "volatility": 0.30},
        ]
        pos = {"ticker": "AAPL", "shares": 100, "price": 150.0, "days_to_earnings": None}

        with (
            patch("src.services.covered_call_screener._fetch_stock_positions",
                  new=AsyncMock(return_value=[pos])),
            patch("src.services.covered_call_screener._fetch_open_calls",
                  new=AsyncMock(return_value=[])),
            patch("src.services.covered_call_screener._fetch_call_chain",
                  new=AsyncMock(return_value=chain_options)),
            patch("src.auth.account_resolver.list_accounts",
                  new=AsyncMock(return_value=[{"hashValue": "abc123"}])),
            patch("src.services.covered_call_screener.fetch_realised_vols",
                  new=AsyncMock(return_value={"AAPL": 0.25})),
        ):
            results = await run_screener(client=client, account_hash="abc123")

        result = results[0]
        ann_yield = _annualised_yield(1.50, 150.0, 35)
        expected = _compute_composite_score(_vol_score(0.30 / 0.25), ann_yield, 0.25)
        assert result.composite_score == expected, (
            f"Balanced score {result.composite_score} != expected {expected}"
        )


class TestFractionalSharesFloor:
    async def test_fractional_100_point_5_floors_to_100_eligible(self):
        """Raw longQuantity=100.5 floors to 100 — eligible, 1 contract."""
        from src.services.covered_call_screener import _fetch_stock_positions

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "securitiesAccount": {
                "positions": [{
                    "instrument": {"assetType": "EQUITY", "symbol": "FRAC"},
                    "longQuantity": 100.5,
                    "marketValue": 15000.0,
                }]
            }
        }
        client.get_account = AsyncMock(return_value=mock_resp)
        positions = await _fetch_stock_positions(client, "abc123")
        assert len(positions) == 1
        assert positions[0]["shares"] == 100

    async def test_fractional_150_point_9_floors_to_150_ineligible(self):
        """Raw longQuantity=150.9 floors to 150 — ineligible (150 % 100 != 0)."""
        from src.services.covered_call_screener import _fetch_stock_positions

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "securitiesAccount": {
                "positions": [{
                    "instrument": {"assetType": "EQUITY", "symbol": "FRAC"},
                    "longQuantity": 150.9,
                    "marketValue": 22500.0,
                }]
            }
        }
        client.get_account = AsyncMock(return_value=mock_resp)
        positions = await _fetch_stock_positions(client, "abc123")
        assert len(positions) == 1
        assert positions[0]["shares"] == 150


# ---------------------------------------------------------------------------
# specs/018 T030 — IV relative to realised volatility (FR-109, D-113)
# ---------------------------------------------------------------------------

class TestIvRvScreener:
    def test_vol_score_band(self):
        from src.services.covered_call_screener import _vol_score

        assert _vol_score(0.5) == 0.0
        assert _vol_score(0.8) == 0.0
        assert _vol_score(1.15) == pytest.approx(50.0)
        assert _vol_score(1.5) == 100.0
        assert _vol_score(3.0) == 100.0
        assert _vol_score(None) is None

    def test_iv_rank_proxy_removed(self):
        import src.services.covered_call_screener as screener

        assert not hasattr(screener, "_iv_rank_from_chain")

    async def _run(self, chain, rv, *, open_calls=None):
        from src.services.covered_call_screener import run_screener

        pos = {"ticker": "AAPL", "shares": 100, "price": 150.0, "days_to_earnings": None}
        rv_mock = AsyncMock(return_value={"AAPL": rv})
        with (
            patch("src.services.covered_call_screener._fetch_stock_positions", new=AsyncMock(return_value=[pos])),
            patch("src.services.covered_call_screener._fetch_open_calls", new=AsyncMock(return_value=open_calls or [])),
            patch("src.services.covered_call_screener._fetch_call_chain", new=AsyncMock(return_value=chain)),
            patch("src.auth.account_resolver.list_accounts", new=AsyncMock(return_value=[{"hashValue": "abc123"}])),
            patch("src.services.covered_call_screener.fetch_realised_vols", new=rv_mock),
        ):
            results = await run_screener(client=_make_client(), account_hash="abc123")
        return results[0], rv_mock

    _CHAIN = [{"dte": 35, "strike": 155.0, "expiry": "2026-06-20", "delta": 0.25, "bid": 1.50,
               "open_interest": 200, "volatility": 0.30}]

    async def test_iv_from_recommended_call_and_ratio(self):
        result, rv_mock = await self._run(self._CHAIN, 0.20)
        assert result.implied_volatility == pytest.approx(0.30)
        assert result.realised_volatility == pytest.approx(0.20)
        assert result.iv_rv_ratio == pytest.approx(1.5)
        assert result.vol_score == pytest.approx(100.0)
        rv_mock.assert_awaited_once()
        assert rv_mock.await_args.args[1] == {"AAPL"}

    async def test_rv_unavailable_contributes_nothing(self):
        from src.services.covered_call_screener import _annualised_yield, _compute_composite_score

        result, _ = await self._run(self._CHAIN, None)
        assert result.implied_volatility == pytest.approx(0.30)
        assert result.iv_rv_ratio is None
        assert result.vol_score is None
        expected = _compute_composite_score(0.0, _annualised_yield(1.50, 150.0, 35), 0.25)
        assert result.composite_score == expected

    async def test_suppressed_row_has_no_iv(self):
        result, _ = await self._run(self._CHAIN, 0.20, open_calls=[{"underlying": "AAPL"}])
        assert result.recommendation_status == "suppressed"
        assert result.implied_volatility is None
        assert result.iv_rv_ratio is None
        assert result.vol_score is None
        assert result.realised_volatility == pytest.approx(0.20)

    async def test_fetch_call_chain_returns_contract_volatility_as_decimal(self):
        from src.services.covered_call_screener import _fetch_call_chain

        client = _make_client()
        resp = MagicMock()
        resp.json.return_value = {"callExpDateMap": {"2026-06-20:35": {"155.0": [
            {"delta": 0.25, "bid": 1.5, "openInterest": 200, "volatility": 30.0},
            {"delta": 0.20, "bid": 1.0, "openInterest": 100, "volatility": -999.0},
        ]}}}
        client.get_option_chain = AsyncMock(return_value=resp)
        options = await _fetch_call_chain(client, "AAPL")
        assert options[0]["volatility"] == pytest.approx(0.30)
        assert options[1]["volatility"] is None
