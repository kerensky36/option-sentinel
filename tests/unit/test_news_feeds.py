"""Tests for public financial news feed gathering (specs/017 FR-009; specs/018 FR-116, FR-118)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.data.models import Headline
from src.services import news_feeds
from src.services.news_feeds import FEEDS, fetch_headlines, parse_feed, select_headlines

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
RECENT = "Thu, 25 Sep 2026 10:00:00 GMT"


def _rss(items: list[tuple[str, str, str, str]]) -> bytes:
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link><pubDate>{d}</pubDate>"
        f"<description>{desc}</description></item>"
        for t, link, d, desc in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


class TestParseFeed:
    def test_parses_items(self):
        xml = _rss([("Fed holds rates", "https://www.cnbc.com/a", "Wed, 24 Sep 2026 14:00:00 GMT", "Summary")])
        items = parse_feed("CNBC", xml)
        assert len(items) == 1
        h = items[0]
        assert h.publisher == "CNBC"
        assert h.title == "Fed holds rates"
        assert h.link == "https://www.cnbc.com/a"
        assert h.published is not None and h.published.year == 2026
        assert h.summary == "Summary"

    def test_strips_html_from_summary_and_truncates(self):
        desc = "&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;" + "x" * 1000
        items = parse_feed("Bloomberg", _rss([("T", "https://bloomberg.com/a", "", desc)]))
        assert "<" not in items[0].summary
        assert items[0].summary.startswith("Hello world")
        assert len(items[0].summary) <= 400

    def test_drops_non_http_links(self):
        items = parse_feed("CNBC", _rss([("Bad", "javascript:alert(1)", "", ""), ("Good", "https://x.com/a", "", "")]))
        assert [h.title for h in items] == ["Good"]

    def test_drops_items_without_title(self):
        items = parse_feed("CNBC", _rss([("", "https://x.com/a", "", "")]))
        assert items == []

    def test_garbage_returns_empty(self):
        assert parse_feed("CNBC", b"not xml at all") == []


def _transport(responses: dict[str, bytes | Exception]):
    def handler(request: httpx.Request) -> httpx.Response:
        for prefix, value in responses.items():
            if str(request.url).startswith(prefix):
                if isinstance(value, Exception):
                    raise value
                return httpx.Response(200, content=value)
        return httpx.Response(404)
    return httpx.MockTransport(handler)


class TestFetchHeadlines:
    async def test_merges_dedupes_sorts_and_caps(self):
        cnbc = _rss([
            ("Older CNBC", "https://cnbc.com/1", "Wed, 24 Sep 2026 08:00:00 GMT", ""),
            ("Same story", "https://cnbc.com/2", "Wed, 24 Sep 2026 10:00:00 GMT", ""),
            ("Stale CNBC", "https://cnbc.com/3", "Mon, 01 Sep 2026 10:00:00 GMT", ""),
        ])
        bbg = _rss([
            ("Newest BBG", "https://bloomberg.com/1", "Thu, 25 Sep 2026 11:00:00 GMT", ""),
            ("same STORY", "https://bloomberg.com/2", "Wed, 24 Sep 2026 09:00:00 GMT", ""),
        ])
        responses = {f.url.split("{")[0]: (cnbc if f.publisher == "CNBC" else bbg if f.publisher == "Bloomberg" else _rss([])) for f in FEEDS}
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client, now=NOW)
        titles = [h.title for h in items]
        assert titles[0] == "Newest BBG"
        assert sum(1 for t in titles if t.lower() == "same story") == 1
        assert "Older CNBC" in titles
        assert "Stale CNBC" not in titles  # older than 48 h

    async def test_cap_of_twelve_applied(self):
        many = _rss([(f"T{i}", f"https://cnbc.com/{i}", RECENT, "") for i in range(50)])
        responses = {f.url.split("{")[0]: many for f in FEEDS}
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client, now=NOW)
        assert len(items) == 12

    async def test_failing_feed_is_tolerated(self):
        good = _rss([("Works", "https://finance.yahoo.com/1", RECENT, "")])
        responses = {}
        for f in FEEDS:
            prefix = f.url.split("{")[0]
            responses[prefix] = good if f.publisher == "Yahoo Finance" else httpx.ConnectError("boom")
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client, now=NOW)
        assert [h.title for h in items] == ["Works"]

    async def test_only_ticker_is_sent_to_ticker_feed(self):
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(200, content=_rss([]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await fetch_headlines("SPY", client=client)
        ticker_urls = [u for u in seen if "s=SPY" in u]
        assert len(ticker_urls) == 1
        assert len(seen) == len(FEEDS)

    async def test_rejects_non_ticker_underlying(self):
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(200, content=_rss([]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await fetch_headlines("SPY&evil=1", client=client)
        assert not any("evil" in u for u in seen)

    def test_feeds_cover_three_publishers(self):
        assert {f.publisher for f in FEEDS} == {"CNBC", "Yahoo Finance", "Bloomberg"}
        assert all(f.url.startswith("https://") for f in FEEDS)

    def test_timeout_is_three_seconds(self):
        assert news_feeds.FEED_TIMEOUT_SECONDS == 3.0

    async def test_ticker_feed_items_are_reserved(self):
        general = _rss([(f"Gen {i}", f"https://cnbc.com/{i}", "Thu, 25 Sep 2026 11:30:00 GMT", "") for i in range(20)])
        ticker = _rss([(f"SPY {i}", f"https://finance.yahoo.com/t{i}", "Thu, 25 Sep 2026 09:00:00 GMT", "") for i in range(8)])

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=ticker if "s=SPY" in str(request.url) else general)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            items = await fetch_headlines("SPY", client=client, now=NOW)
        assert len(items) == 12
        assert sum(1 for h in items if h.title.startswith("SPY ")) == 5


def _h(title: str, hours_ago: float | None, publisher="CNBC") -> Headline:
    return Headline(
        publisher=publisher,
        title=title,
        link=f"https://x.com/{abs(hash(title))}",
        published=None if hours_ago is None else NOW - timedelta(hours=hours_ago),
    )


class TestSelectHeadlines:
    """specs/018 FR-116, research D-112."""

    def test_drops_undated_and_older_than_48h(self):
        out = select_headlines([], [_h("undated", None), _h("old", 49), _h("fresh", 47)], now=NOW)
        assert [h.title for h in out] == ["fresh"]

    def test_ticker_quota_then_fill_with_general(self):
        ticker = [_h(f"t{i}", i + 10) for i in range(7)]
        general = [_h(f"g{i}", i) for i in range(20)]
        out = select_headlines(ticker, general, now=NOW)
        assert len(out) == 12
        assert [h.title for h in out if h.title.startswith("t")] == ["t0", "t1", "t2", "t3", "t4"]
        assert [h.title for h in out if h.title.startswith("g")] == [f"g{i}" for i in range(7)]

    def test_fewer_ticker_items_lets_general_fill(self):
        out = select_headlines([_h("t0", 1)], [_h(f"g{i}", i) for i in range(20)], now=NOW)
        assert len(out) == 12
        assert sum(1 for h in out if h.title.startswith("g")) == 11

    def test_dedupes_across_lists_case_insensitive(self):
        out = select_headlines([_h("Same Story", 1)], [_h("same story", 2), _h("other", 3)], now=NOW)
        assert [h.title for h in out] == ["Same Story", "other"]

    def test_newest_first(self):
        out = select_headlines([_h("t-old", 20)], [_h("g-new", 1), _h("g-mid", 10)], now=NOW)
        assert [h.title for h in out] == ["g-new", "g-mid", "t-old"]

    def test_custom_limits(self):
        out = select_headlines(
            [_h(f"t{i}", i) for i in range(5)], [_h(f"g{i}", i) for i in range(5)],
            now=NOW, limit=4, ticker_quota=1,
        )
        assert len(out) == 4
        assert sum(1 for h in out if h.title.startswith("t")) == 1
