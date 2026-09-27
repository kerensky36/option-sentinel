"""Named figures the quorum may cite (specs/020 D-304, data-model.md FigureCatalog).

Pure module. Every number shown in a seat's cited-figure chips or in the
quorum summary comes from here — a model only ever names a figure, never
writes its value. Unavailable figures are left out, never zero-filled
(specs/018 FR-105).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from src.data.models import AnalystVote, CitedFigure, PositionContext, TallyEntry

MAX_CITED = 5
MAX_BREAKEVENS = 4

_SEAT_SHORT = {
    "greeks_exposure": "Greeks",
    "volatility_pricing": "Volatility",
    "time_decay_pnl": "Time decay",
    "strike_assignment": "Strike",
    "macro_news_overlay": "Macro",
}


@dataclass(frozen=True)
class Figure:
    name: str
    label: str
    value: float
    display: str


def _sign(v: float) -> str:
    return "-" if v < 0 else ""


def _money(v: float) -> str:
    a = abs(v)
    body = f"{a:,.0f}" if a >= 1000 else f"{a:,.2f}"
    return f"{_sign(v)}${body}"


def _pct(v: float) -> str:
    a = abs(v)
    return f"{_sign(v)}{a:.1f}%" if a < 10 else f"{_sign(v)}{a:.0f}%"


def _ratio(v: float) -> str:
    return f"{v:.2f}×"


def _shares(v: float) -> str:
    return f"{v:+.0f} sh"


def _days(v: float) -> str:
    return f"{int(v)} d"


def _count(v: float) -> str:
    return str(int(v))


FORMATTERS: dict[str, Callable[[float], str]] = {
    "money": _money,
    "pct": _pct,
    "ratio": _ratio,
    "shares": _shares,
    "days": _days,
    "count": _count,
}


def _add(cat: dict[str, Figure], name: str, label: str, value, kind: str, scale: float = 1.0) -> None:
    if value is None:
        return
    v = float(value) * scale
    if not math.isfinite(v):
        return
    cat[name] = Figure(name=name, label=label, value=v, display=FORMATTERS[kind](v))


def build(ctx: PositionContext) -> dict[str, Figure]:
    """Catalog for one position: position-level figures, then per-leg figures in leg order."""
    cat: dict[str, Figure] = {}
    pf = ctx.position_fundamentals
    _add(cat, "net_delta", "Net delta", pf.net_position_delta, "shares")
    _add(cat, "net_theta_day", "Theta/day", pf.net_dollar_theta, "money")
    _add(cat, "net_vega", "Vega", pf.net_dollar_vega, "money")
    _add(cat, "max_profit", "Max profit", pf.max_profit, "money")
    _add(cat, "max_loss", "Max loss", pf.max_loss, "money")
    _add(cat, "captured_pct", "Captured", pf.pct_max_profit_captured, "pct")
    for i, be in enumerate(pf.breakevens[:MAX_BREAKEVENS], start=1):
        _add(cat, f"breakeven_{i}", "Breakeven" if i == 1 else f"Breakeven {i}", be, "money")
    _add(cat, "dte", "DTE", ctx.min_days_to_expiry, "days")

    single = len(ctx.legs) == 1
    for n, leg in enumerate(ctx.legs, start=1):
        def label(text: str) -> str:
            return text[:1].upper() + text[1:] if single else f"Leg {n} {text}"

        f = leg.fundamentals
        _add(cat, f"leg{n}_strike", label("strike"), leg.strike, "money")
        _add(cat, f"leg{n}_spot", label("spot"), leg.underlying_price, "money")
        _add(cat, f"leg{n}_iv", label("IV"), leg.implied_volatility, "pct", 100)
        _add(cat, f"leg{n}_rv", label("RV"), f.realised_volatility, "pct", 100)
        _add(cat, f"leg{n}_iv_rv", label("IV/RV"), f.iv_rv_ratio, "ratio")
        _add(cat, f"leg{n}_moneyness", label("moneyness"), f.moneyness_pct, "pct")
        _add(cat, f"leg{n}_prob_itm", label("P(ITM)"), f.prob_itm, "pct", 100)
    return cat


def add_tally(
    catalog: dict[str, Figure], tally: Sequence[TallyEntry], votes: Sequence[AnalystVote]
) -> dict[str, Figure]:
    """Return a new catalog with the vote counts and each voting seat's confidence."""
    cat = dict(catalog)
    counts = {t.action: t.votes for t in tally}
    _add(cat, "votes_close", "Close votes", counts.get("CLOSE", 0), "count")
    _add(cat, "votes_hold", "Hold votes", counts.get("HOLD", 0), "count")
    _add(cat, "votes_roll", "Roll votes", counts.get("ROLL", 0), "count")
    valid = [v for v in votes if not v.abstained and v.action is not None]
    _add(cat, "valid_votes", "Valid votes", len(valid), "count")
    _add(cat, "seats", "Seats", len(votes), "count")
    for v in valid:
        short = _SEAT_SHORT.get(v.seat, v.seat)[:12]
        _add(cat, f"confidence_{v.seat}", f"{short} confidence", v.confidence, "pct", 100)
    return cat


def resolve_cited(names: Iterable[str], catalog: dict[str, Figure]) -> list[CitedFigure]:
    """Known, de-duplicated catalog names (in the seat's order), at most five."""
    out: list[CitedFigure] = []
    seen: set[str] = set()
    for name in names:
        if name in seen or name not in catalog:
            continue
        seen.add(name)
        fig = catalog[name]
        out.append(CitedFigure(name=fig.name, label=fig.label, display=fig.display))
        if len(out) == MAX_CITED:
            break
    return out
