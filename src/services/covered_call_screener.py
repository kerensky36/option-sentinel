"""Covered call screener — ranks long stock positions by CC income potential."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class CoveredCallCandidate:
    ticker: str
    shares: int
    stock_price: float
    iv_rank: float | None
    recommended_strike: float | None
    recommended_expiry: str | None
    bid_premium: float | None
    annualised_yield: float | None
    call_delta: float | None
    days_to_earnings: int | None
    composite_score: float
    recommendation_status: str  # ranked | earnings_risk | call_written | no_liquid_options


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
    yield_score   = _compute_yield_score(annualised_yield_pct)
    delta_safety  = _compute_delta_safety(call_delta)
    raw = iv_rank * 0.50 + yield_score * 0.30 + delta_safety * 0.20
    return round(min(100.0, max(0.0, raw)), 1)


# ── Option selection ──────────────────────────────────────────────────────────

_DTE_MIN = 30
_DTE_MAX = 45
_MIN_BID = 0.05
_MIN_OI   = 100


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

def _apply_suppression(candidate: CoveredCallCandidate) -> CoveredCallCandidate:
    """Overwrite status for earnings risk; other statuses (call_written,
    no_liquid_options) are already set before this is called."""
    if candidate.recommendation_status in ("call_written", "no_liquid_options"):
        return candidate
    dte = candidate.days_to_earnings
    if dte is not None and dte <= 7:
        return CoveredCallCandidate(**{**candidate.__dict__, "recommendation_status": "earnings_risk"})
    return candidate


# ── IV Rank proxy ─────────────────────────────────────────────────────────────

def _iv_rank_from_chain(chain_volatility: float | None) -> float | None:
    """Normalise raw chain volatility (decimal, e.g. 0.35) to an 0–100 rank proxy.
    True IV Rank requires a 52-week history; this approximates using absolute level:
    0% IV → 0, 50%+ IV → 100."""
    if chain_volatility is None:
        return None
    return round(min(100.0, float(chain_volatility) * 200.0), 1)


# ── Annualised yield ──────────────────────────────────────────────────────────

def _annualised_yield(bid: float, stock_price: float, dte: int) -> float:
    if stock_price <= 0 or dte <= 0:
        return 0.0
    return round((bid / stock_price) * (365.0 / dte) * 100.0, 2)


# ── Main screener entry point ─────────────────────────────────────────────────

async def run_screener(client=None) -> list[CoveredCallCandidate]:
    """Fetch stock positions and option chains; return ranked candidates."""
    account_id = os.environ.get("SCHWAB_CC_ACCOUNT_ID", "")
    if not account_id:
        return []

    if client is None:
        from src.auth.schwab_oauth import get_schwab_client
        client = await get_schwab_client()

    from src.auth.account_resolver import resolve_account_hash
    account_id = await resolve_account_hash(client, account_id)

    stock_positions = await _fetch_stock_positions(client, account_id)
    open_calls      = await _fetch_open_calls(client, account_id)
    tickers_with_call = {c["underlying"] for c in open_calls}

    candidates: list[CoveredCallCandidate] = []
    for pos in stock_positions:
        ticker      = pos["ticker"]
        shares      = pos["shares"]
        stock_price = pos["price"]

        if ticker in tickers_with_call:
            candidates.append(CoveredCallCandidate(
                ticker=ticker, shares=shares, stock_price=stock_price,
                iv_rank=None, recommended_strike=None, recommended_expiry=None,
                bid_premium=None, annualised_yield=None, call_delta=None,
                days_to_earnings=pos.get("days_to_earnings"),
                composite_score=0.0, recommendation_status="call_written",
            ))
            continue

        chain_options = await _fetch_call_chain(client, ticker)
        best = _find_best_call(chain_options)
        iv_rank = _iv_rank_from_chain(pos.get("volatility"))

        if best is None:
            candidates.append(CoveredCallCandidate(
                ticker=ticker, shares=shares, stock_price=stock_price,
                iv_rank=iv_rank, recommended_strike=None, recommended_expiry=None,
                bid_premium=None, annualised_yield=None, call_delta=None,
                days_to_earnings=pos.get("days_to_earnings"),
                composite_score=0.0, recommendation_status="no_liquid_options",
            ))
            continue

        ann_yield = _annualised_yield(best["bid"], stock_price, best["dte"])
        score = _compute_composite_score(
            iv_rank=iv_rank or 0.0,
            annualised_yield_pct=ann_yield,
            call_delta=best["delta"],
        )

        candidate = CoveredCallCandidate(
            ticker=ticker,
            shares=shares,
            stock_price=stock_price,
            iv_rank=iv_rank,
            recommended_strike=best["strike"],
            recommended_expiry=best["expiry"],
            bid_premium=best["bid"],
            annualised_yield=ann_yield,
            call_delta=best["delta"],
            days_to_earnings=pos.get("days_to_earnings"),
            composite_score=score,
            recommendation_status="ranked",
        )
        candidates.append(_apply_suppression(candidate))

    ranked   = sorted(
        [c for c in candidates if c.recommendation_status == "ranked"],
        key=lambda c: c.composite_score, reverse=True,
    )
    other    = [c for c in candidates if c.recommendation_status != "ranked"]
    return ranked + other


# ── Schwab data fetchers (injectable for testing) ─────────────────────────────

async def _fetch_stock_positions(client, account_id: str) -> list[dict]:
    resp = await client.get_account(account_id, fields=[client.Account.Fields.POSITIONS])
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
            "volatility": pos.get("instrument", {}).get("volatility"),
            "days_to_earnings": _days_to_earnings(instrument.get("symbol", "")),
        })
    return results


async def _fetch_open_calls(client, account_id: str) -> list[dict]:
    """Return list of open short call option positions in the account."""
    resp = await client.get_account(account_id, fields=[client.Account.Fields.POSITIONS])
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
        # exp_key format: "2025-06-20:35" (date:dte)
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


# ── DB persistence ────────────────────────────────────────────────────────────

async def save_screener_results(session, candidates: list[CoveredCallCandidate]) -> datetime:
    """Replace all screener_result rows with the new candidates. Returns refreshed_at."""
    from sqlalchemy import delete
    from src.data.models import ScreenerResult

    refreshed_at = datetime.utcnow()
    await session.execute(delete(ScreenerResult))
    for i, c in enumerate(candidates):
        session.add(ScreenerResult(
            sort_order=i,
            ticker=c.ticker,
            shares=c.shares,
            stock_price=c.stock_price,
            iv_rank=c.iv_rank,
            recommended_strike=c.recommended_strike,
            recommended_expiry=c.recommended_expiry,
            bid_premium=c.bid_premium,
            annualised_yield=c.annualised_yield,
            call_delta=c.call_delta,
            days_to_earnings=c.days_to_earnings,
            composite_score=c.composite_score,
            recommendation_status=c.recommendation_status,
            refreshed_at=refreshed_at,
        ))
    await session.commit()
    return refreshed_at


async def load_screener_results(session) -> tuple[list[CoveredCallCandidate], datetime | None]:
    """Load cached screener results from DB. Returns (candidates, refreshed_at)."""
    from sqlalchemy import select
    from src.data.models import ScreenerResult

    rows = (await session.execute(
        select(ScreenerResult).order_by(ScreenerResult.sort_order)
    )).scalars().all()

    if not rows:
        return [], None

    candidates = [
        CoveredCallCandidate(
            ticker=r.ticker,
            shares=r.shares,
            stock_price=r.stock_price,
            iv_rank=r.iv_rank,
            recommended_strike=r.recommended_strike,
            recommended_expiry=r.recommended_expiry,
            bid_premium=r.bid_premium,
            annualised_yield=r.annualised_yield,
            call_delta=r.call_delta,
            days_to_earnings=r.days_to_earnings,
            composite_score=r.composite_score,
            recommendation_status=r.recommendation_status,
        )
        for r in rows
    ]
    return candidates, rows[0].refreshed_at


async def refresh_and_cache(session) -> tuple[list[CoveredCallCandidate], datetime]:
    """Run live screener, persist to DB, return (candidates, refreshed_at)."""
    candidates = await run_screener()
    refreshed_at = await save_screener_results(session, candidates)
    logger.info("Screener cache refreshed — %d candidates", len(candidates))
    return candidates, refreshed_at
