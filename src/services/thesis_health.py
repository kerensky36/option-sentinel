import math
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Position, ThesisHealthSnapshot


def compute_score(position: Position) -> float:
    """Return 0–100 thesis health score for a single position leg.

    50 = breakeven, 100 = full profit realised, 0 = full loss.
    """
    pnl = float(position.unrealised_pnl or 0)
    cost = float(position.opening_credit_debit or 0)
    qty = abs(position.quantity)
    basis = abs(cost * qty * 100)
    if basis > 0:
        raw = (pnl / basis) * 50 + 50
    else:
        raw = 50.0
    return max(0.0, min(100.0, raw))


async def upsert_snapshot(session: AsyncSession, position: Position) -> None:
    """Insert or update today's health snapshot for a position (only if thesis assigned)."""
    if not position.thesis_id:
        return
    today = date.today()
    score = compute_score(position)
    result = await session.execute(
        select(ThesisHealthSnapshot).where(
            ThesisHealthSnapshot.position_id == str(position.id),
            ThesisHealthSnapshot.snapshot_date == today,
        )
    )
    snap = result.scalar_one_or_none()
    if snap:
        snap.score = score
    else:
        session.add(ThesisHealthSnapshot(
            position_id=str(position.id),
            snapshot_date=today,
            score=score,
        ))


def compute_group_gauge_svg(pos_list: list, snapshots: dict[str, list]) -> str:
    """Build gauge + sparkline SVG for a position group.

    snapshots: {str(position_id): [ThesisHealthSnapshot ordered by date]}
    Returns empty string if no thesis is attached to any leg.
    """
    if not any(p.thesis for p in pos_list):
        return ""

    # Aggregate daily scores across all legs (average per date)
    date_buckets: dict[str, list[float]] = {}
    for p in pos_list:
        pid = str(p.id)
        for snap in snapshots.get(pid, []):
            key = str(snap.snapshot_date)
            date_buckets.setdefault(key, []).append(snap.score)

    history = [
        sum(scores) / len(scores)
        for _, scores in sorted(date_buckets.items())
    ]

    # Current score: average live score across all legs
    current = sum(compute_score(p) for p in pos_list) / len(pos_list)

    # Always append today's live score so the gauge reflects real-time P&L
    today_key = str(date.today())
    if not history or sorted(date_buckets)[-1] != today_key:
        history.append(current)
    else:
        history[-1] = current

    return _render_gauge_svg(current, history[-14:])


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

def _arc_point(cx: float, cy: float, r: float, angle_rad: float) -> tuple[float, float]:
    return cx + r * math.cos(angle_rad), cy - r * math.sin(angle_rad)


def _render_gauge_svg(score: float, history: list[float]) -> str:
    W, H = 320, 210
    cx, cy, r = 160, 148, 108
    sw = 22  # arc stroke width

    # Color bands
    if score >= 67:
        color, shadow = "#10b981", "rgba(16,185,129,0.35)"
    elif score >= 34:
        color, shadow = "#f59e0b", "rgba(245,158,11,0.35)"
    else:
        color, shadow = "#ef4444", "rgba(239,68,68,0.35)"

    sx, sy = cx - r, cy  # arc start (left = 0 score)

    # Colored arc end point
    end_angle = math.pi * (1.0 - score / 100.0)
    ex, ey = _arc_point(cx, cy, r, end_angle)
    large_arc = 1 if score > 50 else 0

    if score >= 99.9:
        arc_d = f"M {sx:.1f},{sy:.1f} A {r} {r} 0 1 1 {cx+r-0.01:.2f},{sy:.1f}"
    elif score <= 0.1:
        arc_d = None
    else:
        arc_d = f"M {sx:.1f},{sy:.1f} A {r} {r} 0 {large_arc} 1 {ex:.1f},{ey:.1f}"

    bg_d = f"M {sx:.1f},{sy:.1f} A {r} {r} 0 1 1 {cx+r:.1f},{sy:.1f}"

    # Tick marks at 0, 25, 50, 75, 100
    def tick(s: float) -> str:
        a = math.pi * (1 - s / 100)
        ix, iy = _arc_point(cx, cy, r - sw / 2 - 3, a)
        ox, oy = _arc_point(cx, cy, r + sw / 2 + 5, a)
        return f'<line x1="{ix:.1f}" y1="{iy:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" stroke="#374151" stroke-width="1.5"/>'

    ticks = "".join(tick(s) for s in (0, 25, 50, 75, 100))

    # Tick labels
    def tick_label(s: float, label: str) -> str:
        a = math.pi * (1 - s / 100)
        lx, ly = _arc_point(cx, cy, r + sw / 2 + 18, a)
        return f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#4b5563">{label}</text>'

    tick_labels = "".join([
        tick_label(0, "0"),
        tick_label(25, "25"),
        tick_label(50, "50"),
        tick_label(75, "75"),
        tick_label(100, "100"),
    ])

    # Score integer + change indicator
    score_int = int(round(score))
    if len(history) >= 2:
        delta = history[-1] - history[-2]
        delta_str = f"+{delta:.0f}" if delta >= 0 else f"{delta:.0f}"
        delta_color = "#10b981" if delta >= 0 else "#ef4444"
        delta_el = f'<text x="{cx}" y="{cy+26}" text-anchor="middle" font-size="13" font-family="ui-monospace,monospace" fill="{delta_color}">{delta_str}</text>'
    else:
        delta_el = ""

    # Sparkline
    sparkline = ""
    if len(history) >= 2:
        sp_w, sp_h = 210, 34
        sp_x0 = (W - sp_w) / 2
        sp_y0 = H - sp_h - 4

        def spx(i: int) -> float:
            return sp_x0 + i / (len(history) - 1) * sp_w

        def spy(v: float) -> float:
            return sp_y0 + sp_h - (max(0.0, min(100.0, v)) / 100.0) * sp_h

        pts = " ".join(f"{spx(i):.1f},{spy(v):.1f}" for i, v in enumerate(history))
        trend = "#10b981" if history[-1] >= history[0] else "#ef4444"

        fill_d = (
            f"M {spx(0):.1f},{sp_y0+sp_h:.1f} "
            + " ".join(f"L {spx(i):.1f},{spy(v):.1f}" for i, v in enumerate(history))
            + f" L {spx(len(history)-1):.1f},{sp_y0+sp_h:.1f} Z"
        )

        zero_y = spy(50)
        sparkline = (
            f'<text x="{W/2:.0f}" y="{sp_y0-7:.0f}" text-anchor="middle" font-size="8" fill="#374151" letter-spacing="1.5">TREND</text>'
            f'<path d="{fill_d}" fill="{trend}" opacity="0.12"/>'
            f'<line x1="{sp_x0:.1f}" y1="{zero_y:.1f}" x2="{sp_x0+sp_w:.1f}" y2="{zero_y:.1f}" stroke="#374151" stroke-width="0.7" stroke-dasharray="3,2"/>'
            f'<polyline points="{pts}" fill="none" stroke="{trend}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    arc_el = (
        f'<path d="{arc_d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" filter="url(#tglow)"/>'
        if arc_d else ""
    )

    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">'
        f'<defs>'
        f'<filter id="tglow" x="-40%" y="-40%" width="180%" height="180%">'
        f'<feGaussianBlur stdDeviation="5" result="blur"/>'
        f'<feMerge><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        f'</filter>'
        f'</defs>'
        f'<path d="{bg_d}" fill="none" stroke="#1f2937" stroke-width="{sw}" stroke-linecap="round"/>'
        f'{ticks}'
        f'{tick_labels}'
        f'{arc_el}'
        f'<text x="{cx}" y="{cy-14}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="54" font-weight="700" fill="{color}">{score_int}</text>'
        f'{delta_el}'
        f'<text x="{cx}" y="{cy+45}" text-anchor="middle" font-size="10" fill="#6b7280" letter-spacing="2">THESIS HEALTH</text>'
        f'{sparkline}'
        f'</svg>'
    )
