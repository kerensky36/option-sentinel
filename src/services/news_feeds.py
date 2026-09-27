"""Public financial news feeds for the quorum's news overlay seat.

specs/017 FR-009 (research D-004); selection rules from specs/018 FR-116 (D-112).

Headlines only — title, summary, link. Article bodies (often paywalled) are
never fetched. The only request-specific value sent anywhere is the
underlying ticker symbol, to Yahoo Finance's per-ticker feed.
"""
from __future__ import annotations

import asyncio
import calendar
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from src.data.models import Headline

_log = logging.getLogger(__name__)

FEED_TIMEOUT_SECONDS = 3.0
HEADLINE_LIMIT = 12
TICKER_QUOTA = 5
MAX_AGE = timedelta(hours=48)
_TITLE_MAX = 300
_SUMMARY_MAX = 400
_TICKER_RE = re.compile(r"^[A-Z0-9.\-/^]{1,10}$")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class FeedSource:
    publisher: str
    url: str  # may contain {ticker}


FEEDS: tuple[FeedSource, ...] = (
    FeedSource("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    FeedSource("CNBC", "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    FeedSource("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    FeedSource("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
    FeedSource(
        "Yahoo Finance",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    ),
)


def _clean(text: str, limit: int) -> str:
    text = html.unescape(_TAG_RE.sub(" ", html.unescape(text or "")))
    return _WS_RE.sub(" ", text).strip()[:limit]


def parse_feed(publisher: str, content: bytes) -> list[Headline]:
    """Parse RSS/Atom bytes into Headlines; malformed input yields []."""
    try:
        parsed = feedparser.parse(content)
    except Exception:  # feedparser is lenient, but never let one feed break the quorum
        return []

    items: list[Headline] = []
    for entry in parsed.entries:
        title = _clean(entry.get("title", ""), _TITLE_MAX)
        link = (entry.get("link") or "").strip()
        if not title or not link.lower().startswith(("https://", "http://")):
            continue
        published = None
        stamp = entry.get("published_parsed")
        if not stamp and "updated_parsed" in entry.keys():
            stamp = entry.get("updated_parsed")
        if stamp:
            published = datetime.fromtimestamp(calendar.timegm(stamp), tz=timezone.utc)
        items.append(
            Headline(
                publisher=publisher,
                title=title,
                link=link,
                published=published,
                summary=_clean(entry.get("summary", ""), _SUMMARY_MAX),
            )
        )
    return items


async def _fetch_one(client: httpx.AsyncClient, source: FeedSource, ticker: str | None) -> list[Headline]:
    if "{ticker}" in source.url:
        if ticker is None:
            return []
        url = source.url.format(ticker=ticker)
    else:
        url = source.url
    try:
        resp = await client.get(url, timeout=FEED_TIMEOUT_SECONDS, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        _log.info("news feed unavailable publisher=%s error=%s", source.publisher, type(exc).__name__)
        return []
    return parse_feed(source.publisher, resp.content)


def select_headlines(
    ticker_items: list[Headline],
    general_items: list[Headline],
    *,
    now: datetime,
    limit: int = HEADLINE_LIMIT,
    ticker_quota: int = TICKER_QUOTA,
    max_age: timedelta = MAX_AGE,
) -> list[Headline]:
    """Recent, de-duplicated headlines: up to `ticker_quota` from the underlying's own
    feed, filled to `limit` with the newest general headlines; newest first."""
    cutoff = now - max_age
    seen: set[str] = set()

    def take(items: list[Headline], count: int) -> list[Headline]:
        kept: list[Headline] = []
        fresh = (h for h in items if h.published and h.published >= cutoff)
        for h in sorted(fresh, key=lambda h: h.published, reverse=True):
            if len(kept) == count:
                break
            key = h.title.casefold()
            if key not in seen:
                seen.add(key)
                kept.append(h)
        return kept

    chosen = take(ticker_items, min(ticker_quota, limit))
    chosen += take(general_items, limit - len(chosen))
    chosen.sort(key=lambda h: h.published, reverse=True)
    return chosen


async def fetch_headlines(
    underlying: str,
    *,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
    limit: int = HEADLINE_LIMIT,
) -> list[Headline]:
    """Fetch all feeds concurrently, then pick recent headlines per `select_headlines`."""
    ticker = underlying.strip().upper()
    if not _TICKER_RE.match(ticker):
        ticker = None

    own_client = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": "OptionSentinel/1.0"})
    try:
        results = await asyncio.gather(*(_fetch_one(client, f, ticker) for f in FEEDS))
    finally:
        if own_client:
            await client.aclose()

    ticker_items: list[Headline] = []
    general_items: list[Headline] = []
    for source, items in zip(FEEDS, results):
        (ticker_items if "{ticker}" in source.url else general_items).extend(items)

    return select_headlines(
        ticker_items, general_items, now=now or datetime.now(timezone.utc), limit=limit
    )
