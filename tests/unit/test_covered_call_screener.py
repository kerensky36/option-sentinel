from src.services.covered_call_screener import (
    _compute_composite_score,
    _compute_delta_safety,
    _compute_yield_score,
    _find_best_call,
    _apply_suppression,
    CoveredCallCandidate,
)

# ── Composite score components ────────────────────────────────────────────────

def test_yield_score_normalises_20pct_to_100():
    assert _compute_yield_score(20.0) == 100.0


def test_yield_score_normalises_10pct_to_50():
    assert _compute_yield_score(10.0) == 50.0


def test_yield_score_capped_at_100():
    assert _compute_yield_score(999.0) == 100.0


def test_yield_score_zero_for_no_yield():
    assert _compute_yield_score(0.0) == 0.0


def test_delta_safety_perfect_at_025():
    assert _compute_delta_safety(0.25) == 100.0


def test_delta_safety_zero_at_050():
    assert _compute_delta_safety(0.50) == 0.0


def test_delta_safety_zero_at_zero_delta():
    assert _compute_delta_safety(0.0) == 0.0


def test_delta_safety_partial_at_030():
    score = _compute_delta_safety(0.30)
    assert 0 < score < 100


def test_composite_score_high_iv_ranks_above_low_iv():
    high = _compute_composite_score(iv_rank=90, annualised_yield_pct=15.0, call_delta=0.25)
    low  = _compute_composite_score(iv_rank=20, annualised_yield_pct=15.0, call_delta=0.25)
    assert high > low


def test_composite_score_clamped_0_to_100():
    score = _compute_composite_score(iv_rank=100, annualised_yield_pct=100.0, call_delta=0.25)
    assert 0.0 <= score <= 100.0


def test_composite_score_zero_inputs():
    score = _compute_composite_score(iv_rank=0, annualised_yield_pct=0.0, call_delta=0.50)
    assert score == 0.0


# ── _find_best_call ───────────────────────────────────────────────────────────

def _make_option(dte: int, delta: float, bid: float, oi: int, strike: float) -> dict:
    return {"dte": dte, "delta": delta, "bid": bid, "open_interest": oi, "strike": strike, "expiry": "2025-06-20"}


def test_find_best_call_picks_closest_to_025_delta():
    options = [
        _make_option(35, 0.20, 1.50, 500, 200),
        _make_option(35, 0.25, 1.20, 400, 205),  # closest to 0.25
        _make_option(35, 0.35, 0.90, 300, 210),
    ]
    best = _find_best_call(options)
    assert best["strike"] == 205


def test_find_best_call_excludes_low_bid():
    options = [
        _make_option(35, 0.25, 0.03, 500, 200),  # bid < 0.05
        _make_option(35, 0.28, 0.10, 500, 205),
    ]
    best = _find_best_call(options)
    assert best["strike"] == 205


def test_find_best_call_excludes_low_oi():
    options = [
        _make_option(35, 0.25, 1.00, 50, 200),   # OI < 100
        _make_option(35, 0.28, 1.00, 200, 205),
    ]
    best = _find_best_call(options)
    assert best["strike"] == 205


def test_find_best_call_excludes_out_of_dte_window():
    options = [
        _make_option(20, 0.25, 1.00, 500, 200),  # DTE < 30
        _make_option(50, 0.25, 1.00, 500, 205),  # DTE > 45
        _make_option(38, 0.25, 1.00, 500, 210),  # valid
    ]
    best = _find_best_call(options)
    assert best["strike"] == 210


def test_find_best_call_returns_none_when_no_liquid_options():
    options = [
        _make_option(35, 0.25, 0.02, 50, 200),
    ]
    assert _find_best_call(options) is None


# ── Suppression rules ─────────────────────────────────────────────────────────

def _base_candidate(**kwargs) -> CoveredCallCandidate:
    defaults = dict(
        ticker="AAPL", shares=100, stock_price=200.0, iv_rank=60.0,
        recommended_strike=210.0, recommended_expiry="2025-06-20",
        bid_premium=1.50, annualised_yield=15.0, call_delta=0.25,
        days_to_earnings=30, composite_score=72.0,
        recommendation_status="ranked",
    )
    defaults.update(kwargs)
    return CoveredCallCandidate(**defaults)


def test_suppression_earnings_within_7_days():
    c = _base_candidate(days_to_earnings=5)
    result = _apply_suppression(c)
    assert result.recommendation_status == "earnings_risk"


def test_suppression_earnings_exactly_7_days_is_suppressed():
    c = _base_candidate(days_to_earnings=7)
    result = _apply_suppression(c)
    assert result.recommendation_status == "earnings_risk"


def test_suppression_earnings_8_days_not_suppressed():
    c = _base_candidate(days_to_earnings=8)
    result = _apply_suppression(c)
    assert result.recommendation_status == "ranked"


def test_suppression_call_written():
    c = _base_candidate(recommendation_status="call_written")
    result = _apply_suppression(c)
    assert result.recommendation_status == "call_written"


def test_suppression_no_liquid_options():
    c = _base_candidate(
        recommended_strike=None, recommended_expiry=None,
        bid_premium=None, annualised_yield=None, call_delta=None,
        composite_score=0.0, recommendation_status="no_liquid_options",
    )
    result = _apply_suppression(c)
    assert result.recommendation_status == "no_liquid_options"


def test_suppression_earnings_none_does_not_suppress():
    c = _base_candidate(days_to_earnings=None)
    result = _apply_suppression(c)
    assert result.recommendation_status == "ranked"
