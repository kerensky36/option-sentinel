from dataclasses import dataclass, field
from datetime import date


@dataclass
class PositionGroup:
    underlying_symbol: str
    expiry_date: date
    positions: list
    is_spread: bool
    strategy_label: str
    net_pnl: float | None
    net_delta: float | None
    net_gamma: float | None
    net_theta: float | None
    net_vega: float | None
    net_iv: float | None
    dte: int | None
    # Delta bar display helpers
    delta_bar_pct: float      # 0–50 (half the bar, centred at 0)
    delta_bar_dir: str        # 'left' | 'right' | 'none'
    # Theta in dollars per day (net across all legs)
    theta_dollar_day: float | None
    payoff_svg: str = ""
    svg_id: str = ""
    thesis_gauge_svg: str = ""


def group_positions(positions: list, snapshots: dict | None = None) -> list["PositionGroup"]:
    from collections import defaultdict
    buckets: dict[tuple, list] = defaultdict(list)
    for p in positions:
        buckets[(p.underlying_symbol, p.expiry_date)].append(p)

    groups = []
    for (underlying, expiry), pos_list in buckets.items():
        pos_list = sorted(pos_list, key=lambda p: float(p.strike), reverse=True)
        is_spread = len(pos_list) > 1
        strategy = _detect_strategy(pos_list)
        net_pnl = _sum_floats(float(p.unrealised_pnl) for p in pos_list if p.unrealised_pnl is not None)
        net_delta = _net_greek(pos_list, "delta")
        net_gamma = _net_greek(pos_list, "gamma")
        net_theta = _net_greek(pos_list, "theta")
        net_vega = _net_greek(pos_list, "vega")
        net_iv = _avg_iv(pos_list)
        dte = pos_list[0].days_to_expiry

        # Delta bar: normalise to number of total contracts
        total_contracts = sum(abs(p.quantity) for p in pos_list)
        max_exposure = max(total_contracts, 1)
        if net_delta is not None:
            raw_pct = min(abs(net_delta) / max_exposure * 50, 50)
            delta_bar_pct = round(raw_pct, 1)
            delta_bar_dir = "left" if net_delta < 0 else "right" if net_delta > 0 else "none"
        else:
            delta_bar_pct = 0.0
            delta_bar_dir = "none"

        # Dollar theta per day: theta (per share per day) × qty × 100 (shares per contract)
        theta_dollar_day: float | None = None
        for p in pos_list:
            if p.greeks and p.greeks.theta is not None:
                contrib = p.greeks.theta * p.quantity * 100
                theta_dollar_day = (theta_dollar_day or 0.0) + contrib

        svg_id = str(pos_list[0].id).replace("-", "")[:10]
        payoff_svg = _compute_payoff_svg(pos_list, svg_id)

        from src.services.thesis_health import compute_group_gauge_svg
        thesis_gauge_svg = compute_group_gauge_svg(pos_list, snapshots or {})

        groups.append(PositionGroup(
            underlying_symbol=underlying,
            expiry_date=expiry,
            positions=pos_list,
            is_spread=is_spread,
            strategy_label=strategy,
            net_pnl=net_pnl,
            net_delta=net_delta,
            net_gamma=net_gamma,
            net_theta=net_theta,
            net_vega=net_vega,
            net_iv=net_iv,
            dte=dte,
            delta_bar_pct=delta_bar_pct,
            delta_bar_dir=delta_bar_dir,
            theta_dollar_day=theta_dollar_day,
            payoff_svg=payoff_svg,
            svg_id=svg_id,
            thesis_gauge_svg=thesis_gauge_svg,
        ))

    return sorted(groups, key=lambda g: (g.underlying_symbol, str(g.expiry_date)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sum_floats(values) -> float | None:
    total = None
    for v in values:
        total = (total or 0.0) + v
    return total


def _net_greek(positions: list, attr: str) -> float | None:
    total = None
    for p in positions:
        g = p.greeks
        if g is None:
            continue
        val = getattr(g, attr, None)
        if val is not None:
            total = (total or 0.0) + val * p.quantity
    return total


def _avg_iv(positions: list) -> float | None:
    ivs = [p.greeks.implied_volatility for p in positions if p.greeks and p.greeks.implied_volatility is not None]
    return sum(ivs) / len(ivs) if ivs else None


def _detect_strategy(positions: list) -> str:
    if len(positions) == 1:
        p = positions[0]
        side = "Long" if p.quantity > 0 else "Short"
        ptype = "Call" if p.option_type.value == "call" else "Put"
        return f"{side} {ptype}"

    all_puts = all(p.option_type.value == "put" for p in positions)
    all_calls = all(p.option_type.value == "call" for p in positions)
    longs = [p for p in positions if p.quantity > 0]
    shorts = [p for p in positions if p.quantity < 0]

    if len(positions) == 2 and longs and shorts:
        ls = float(longs[0].strike)
        ss = float(shorts[0].strike)
        if all_puts:
            return "Put Debit Spread" if ls > ss else "Put Credit Spread"
        if all_calls:
            return "Call Debit Spread" if ls < ss else "Call Credit Spread"

    if len(positions) == 4 and all_puts and all_calls:
        return "Iron Condor"

    return "Vertical Spread" if len(positions) == 2 else "Spread"


def _compute_payoff_svg(positions: list, svg_id: str, width: int = 220, height: int = 60) -> str:
    if not any(p.opening_credit_debit is not None for p in positions):
        return ""

    strikes = [float(p.strike) for p in positions]
    min_k, max_k = min(strikes), max(strikes)
    sw = max(max_k - min_k, 5)

    s_min = min_k - sw * 1.8
    s_max = max_k + sw * 1.8
    n = 60

    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        S = s_min + (s_max - s_min) * i / n
        pnl = 0.0
        for pos in positions:
            K = float(pos.strike)
            qty = pos.quantity
            cost = float(pos.opening_credit_debit or 0)
            ot = pos.option_type.value if hasattr(pos.option_type, "value") else pos.option_type
            intrinsic = max(K - S, 0) if ot == "put" else max(S - K, 0)
            pnl += (intrinsic - cost) * qty * 100
        pts.append((S, pnl))

    pnls = [p for _, p in pts]
    max_p = max(pnls)
    min_p = min(pnls)
    pnl_range = max(abs(max_p), abs(min_p), 1)

    px, py = 6, 5
    w, h = width - px * 2, height - py * 2

    def sx(S: float) -> float:
        return px + (S - s_min) / (s_max - s_min) * w

    def sy(pnl: float) -> float:
        return py + h / 2 - (pnl / (pnl_range * 2.5)) * h

    zero_y = sy(0)
    zero_pct = max(0.0, min(100.0, (zero_y - py) / h * 100))

    x0 = sx(pts[0][0])
    xn = sx(pts[-1][0])
    fill_path = f"M {x0:.1f},{zero_y:.1f} " + " ".join(f"L {sx(S):.1f},{sy(p):.1f}" for S, p in pts) + f" L {xn:.1f},{zero_y:.1f} Z"
    line_pts = " ".join(f"{sx(S):.1f},{sy(p):.1f}" for S, p in pts)
    gid = f"pg{svg_id}"

    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="{py}" x2="0" y2="{py+h:.0f}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="{zero_pct:.1f}%" stop-color="rgba(16,185,129,0.22)"/>'
        f'<stop offset="{zero_pct:.1f}%" stop-color="rgba(239,68,68,0.22)"/>'
        f'</linearGradient></defs>'
        f'<path d="{fill_path}" fill="url(#{gid})"/>'
        f'<line x1="{px}" y1="{zero_y:.1f}" x2="{width-px}" y2="{zero_y:.1f}" stroke="#374151" stroke-width="0.8" stroke-dasharray="3,2"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="#34D399" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg>'
    )
