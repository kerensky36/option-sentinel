"""Tests for public financial news feed gathering (specs/017 FR-009, FR-012)."""
from __future__ import annotations

import httpx
import pytest

from src.services import news_feeds
from src.services.news_feeds import FEEDS, fetch_headlines, parse_feed


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
            ("Old CNBC", "https://cnbc.com/1", "Mon, 01 Sep 2026 10:00:00 GMT", ""),
            ("Same story", "https://cnbc.com/2", "Tue, 02 Sep 2026 10:00:00 GMT", ""),
        ])
        bbg = _rss([
            ("Newest BBG", "https://bloomberg.com/1", "Wed, 24 Sep 2026 10:00:00 GMT", ""),
            ("same STORY", "https://bloomberg.com/2", "Tue, 02 Sep 2026 09:00:00 GMT", ""),
        ])
        responses = {f.url.split("{")[0]: (cnbc if f.publisher == "CNBC" else bbg if f.publisher == "Bloomberg" else _rss([])) for f in FEEDS}
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client, limit=30)
        titles = [h.title for h in items]
        assert titles[0] == "Newest BBG"
        assert sum(1 for t in titles if t.lower() == "same story") == 1
        assert "Old CNBC" in titles

    async def test_limit_applied(self):
        many = _rss([(f"T{i}", f"https://cnbc.com/{i}", "", "") for i in range(50)])
        responses = {f.url.split("{")[0]: many for f in FEEDS}
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client, limit=30)
        assert len(items) == 30

    async def test_failing_feed_is_tolerated(self):
        good = _rss([("Works", "https://finance.yahoo.com/1", "", "")])
        responses = {}
        for f in FEEDS:
            prefix = f.url.split("{")[0]
            responses[prefix] = good if f.publisher == "Yahoo Finance" else httpx.ConnectError("boom")
        async with httpx.AsyncClient(transport=_transport(responses)) as client:
            items = await fetch_headlines("SPY", client=client)
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

    def test_timeout_is_five_seconds(self):
        assert news_feeds.FEED_TIMEOUT_SECONDS == 5.0
