"""Covered call screener — ranks long stock positions by CC income potential.

Fully stateless: fetches live data from Schwab, computes rankings, returns
a list of ScreenerResultView objects. No database reads or writes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.data.models import ScreenerResultView

logger = logging.getLogger(__name__)


# ── Scoring primitives (pure — testable without I/O) ─────────────────────────

def _compute_yield_score(annualised_yield_pct: float) -> float:
    """Map annualised yield % to 0–100. 20%+ → 100."""
    return min(100.0, annualised_yield_pct * 5.0)


def _compute_delta_safety(call_delta: float) -> float:
    """100 at delta=0.25, falls linearly to 0 at delta=0 or delta=0.50."""
    return max(0.0, 100.0 - abs(call_delta - 0.25) * 400.0)


def _compute_composite_score(
    iv_rank: float,
    annualised_yield_pct: float,
    call_delta: float,
) -> float:
    yield_score  = _compute_yield_score(annualised_yield_pct)
    delta_safety = _compute_delta_safety(call_delta)
    raw = iv_rank * 0.50 + yield_score * 0.30 + delta_safety * 0.20
    return round(min(100.0, max(0.0, raw)), 1)


# ── Option selection ──────────────────────────────────────────────────────────

_DTE_MIN = 30
_DTE_MAX = 45
_MIN_BID = 0.05
_MIN_OI  = 100


def _find_best_call(options: list[dict]) -> dict | None:
    """Return the liquid call in the 30–45 DTE window whose delta is closest to 0.25."""
    liquid = [
        o for o in options
        if _DTE_MIN <= o["dte"] <= _DTE_MAX
        and o["bid"] >= _MIN_BID
        and o["open_interest"] >= _MIN_OI
    ]
    if not liquid:
        return None
    return min(liquid, key=lambda o: abs(o["delta"] - 0.25))


# ── Suppression ───────────────────────────────────────────────────────────────

def _recommendation_status(
    base_status: str,
    days_to_earnings: int | None,
) -> str:
    """Map internal status strings to ScreenerResultView status literals."""
    if base_status == "call_written":
        return "suppressed"
    if base_status == "no_liquid_options":
        return "insufficient_data"
    if days_to_earnings is not None and days_to_earnings <= 7:
        return "suppressed"
    return "recommended"


# ── IV Rank proxy ─────────────────────────────────────────────────────────────

def _iv_rank_from_chain(chain_volatility: float | None) -> float | None:
    """Normalise raw chain volatility (decimal) to a 0–100 rank proxy."""
    if chain_volatility is None:
        return None
    return round(min(100.0, float(chain_volatility) * 200.0), 1)


# ── Annualised yield ──────────────────────────────────────────────────────────

def _annualised_yield(bid: float, stock_price: float, dte: int) -> float:
    if stock_price <= 0 or dte <= 0:
        return 0.0
    return round((bid / stock_price) * (365.0 / dte) * 100.0, 2)


# ── Main screener entry point ─────────────────────────────────────────────────

async def run_screener(client=None) -> list[ScreenerResultView]:
    """Fetch stock positions and option chains; return ranked ScreenerResultView list.

    Args:
        client: Authenticated async schwab-py client. If None, raises ValueError.

    Returns:
        List of ScreenerResultView objects sorted by composite_score descending.
    """
    if client is None:
        raise ValueError("A Schwab client must be provided to run_screener")

    from src.auth.account_resolver import list_accounts
    accounts = await list_accounts(client)
    if not accounts:
        logger.warning("No accounts found on token — screener returning empty results")
        return []
    account_hash = accounts[0]["hashValue"]

    stock_positions = await _fetch_stock_positions(client, account_hash)
    open_calls      = await _fetch_open_calls(client, account_hash)
    tickers_with_call = {c["underlying"] for c in open_calls}

    results: list[ScreenerResultView] = []
    sort_order = 0

    for pos in stock_positions:
        ticker      = pos["ticker"]
        shares      = pos["shares"]
        stock_price = pos["price"]
        iv_rank     = _iv_rank_from_chain(pos.get("volatility"))
        dte_earnings = _days_to_earnings(ticker)

        if ticker in tickers_with_call:
            results.append(ScreenerResultView(
                ticker=ticker,
                shares=shares,
                stock_price=stock_price,
                iv_rank=iv_rank,
                days_to_earnings=dte_earnings,
                composite_score=0.0,
                recommendation_status="suppressed",
                sort_order=sort_order,
            ))
            sort_order += 1
            continue

        chain_options = await _fetch_call_chain(client, ticker)
        best = _find_best_call(chain_options)

        if best is None:
            results.append(ScreenerResultView(
                ticker=ticker,
                shares=shares,
                stock_price=stock_price,
                iv_rank=iv_rank,
                days_to_earnings=dte_earnings,
                composite_score=0.0,
                recommendation_status="insufficient_data",
                sort_order=sort_order,
            ))
            sort_order += 1
            continue

        ann_yield = _annualised_yield(best["bid"], stock_price, best["dte"])
        score = _compute_composite_score(
            iv_rank=iv_rank or 0.0,
            annualised_yield_pct=ann_yield,
            call_delta=best["delta"],
        )
        status = _recommendation_status("ranked", dte_earnings)

        results.append(ScreenerResultView(
            ticker=ticker,
            shares=shares,
            stock_price=stock_price,
            iv_rank=iv_rank,
            recommended_strike=best["strike"],
            recommended_expiry=best["expiry"],
            bid_premium=best["bid"],
            annualised_yield=ann_yield,
            call_delta=best["delta"],
            days_to_earnings=dte_earnings,
            composite_score=score,
            recommendation_status=status,
            sort_order=sort_order,
        ))
        sort_order += 1

    # Sort: recommended first by score, then suppressed, then insufficient_data
    ranked   = sorted(
        [r for r in results if r.recommendation_status == "recommended"],
        key=lambda r: r.composite_score, reverse=True,
    )
    other = [r for r in results if r.recommendation_status != "recommended"]

    # Re-assign sort_order after sorting
    ordered = ranked + other
    for i, r in enumerate(ordered):
        r.sort_order = i

    logger.info("Screener complete — %d results (%d recommended)", len(ordered), len(ranked))
    return ordered


# ── Schwab data fetchers ──────────────────────────────────────────────────────

async def _fetch_stock_positions(client, account_hash: str) -> list[dict]:
    resp = await client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    data = resp.json()
    positions_raw = data.get("securitiesAccount", {}).get("positions", [])
    results = []
    for pos in positions_raw:
        instrument = pos.get("instrument", {})
        if instrument.get("assetType") != "EQUITY":
            continue
        long_qty = int(pos.get("longQuantity", 0))
        if long_qty <= 0:
            continue
        results.append({
            "ticker":    instrument.get("symbol", ""),
            "shares":    long_qty,
            "price":     float(pos.get("marketValue", 0)) / long_qty if long_qty else 0.0,
            "volatility": instrument.get("volatility"),
            "days_to_earnings": _days_to_earnings(instrument.get("symbol", "")),
        })
    return results


async def _fetch_open_calls(client, account_hash: str) -> list[dict]:
    """Return list of open short call option positions in the account."""
    resp = await client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    data = resp.json()
    positions_raw = data.get("securitiesAccount", {}).get("positions", [])
    results = []
    for pos in positions_raw:
        instrument = pos.get("instrument", {})
        if instrument.get("assetType") != "OPTION":
            continue
        if int(pos.get("shortQuantity", 0)) <= 0:
            continue
        symbol = instrument.get("symbol", "")
        if len(symbol) > 6 and symbol[-9].upper() == "C":
            underlying = symbol[:-15].strip()
            results.append({"underlying": underlying})
    return results


async def _fetch_call_chain(client, ticker: str) -> list[dict]:
    """Fetch call option chain for ticker; return flat list of option dicts."""
    today = datetime.now(timezone.utc).date()
    from_date = today + timedelta(days=_DTE_MIN - 2)
    to_date   = today + timedelta(days=_DTE_MAX + 2)

    resp = await client.get_option_chain(
        ticker,
        contract_type=client.Options.ContractType.CALL,
        from_date=from_date,
        to_date=to_date,
        option_type=client.Options.Type.STANDARD,
    )
    data = resp.json()
    options = []
    call_map = data.get("callExpDateMap", {})
    for exp_key, strikes in call_map.items():
        try:
            exp_date_str, dte_str = exp_key.rsplit(":", 1)
            dte = int(dte_str)
        except (ValueError, AttributeError):
            continue
        for strike_str, contracts in strikes.items():
            for contract in contracts:
                options.append({
                    "dte":           dte,
                    "strike":        float(strike_str),
                    "expiry":        exp_date_str,
                    "delta":         abs(float(contract.get("delta", 0) or 0)),
                    "bid":           float(contract.get("bid", 0) or 0),
                    "open_interest": int(contract.get("openInterest", 0) or 0),
                })
    return options


def _days_to_earnings(ticker: str) -> int | None:
    """Placeholder — earnings data not yet integrated. Returns None."""
    return None
