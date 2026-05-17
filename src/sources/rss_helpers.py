from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.models import Article
from src.utils.text_utils import clean_text
from src.utils.time_utils import parse_datetime

logger = logging.getLogger(__name__)


def parse_feed(
    content: bytes | str,
    source_name: str,
    default_language: str | None = None,
    *,
    reliability_score: float = 0.6,
    ownership: str | None = None,
    bias_hint: str | None = None,
    category: str | None = None,
    source_type: str | None = "rss",
    source_url: str | None = None,
    source_tier: int = 4,
    source_role: str = "custom",
    state_affiliated: bool = False,
    propaganda_risk: str = "unknown",
    editorial_context: str | None = None,
) -> list[Article]:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError("feedparser is required for RSS sources") from exc

    parsed = feedparser.parse(content)
    articles: list[Article] = []
    for entry in parsed.entries:
        article = article_from_entry(
            entry,
            source_name,
            default_language,
            reliability_score=reliability_score,
            ownership=ownership,
            bias_hint=bias_hint,
            category=category,
            source_type=source_type,
            source_url=source_url,
            source_tier=source_tier,
            source_role=source_role,
            state_affiliated=state_affiliated,
            propaganda_risk=propaganda_risk,
            editorial_context=editorial_context,
        )
        if article:
            articles.append(article)
    return articles


def article_from_entry(
    entry: Any,
    source_name: str,
    default_language: str | None = None,
    *,
    reliability_score: float = 0.6,
    ownership: str | None = None,
    bias_hint: str | None = None,
    category: str | None = None,
    source_type: str | None = "rss",
    source_url: str | None = None,
    source_tier: int = 4,
    source_role: str = "custom",
    state_affiliated: bool = False,
    propaganda_risk: str = "unknown",
    editorial_context: str | None = None,
) -> Article | None:
    title = clean_text(_get(entry, "title"))
    url = str(_get(entry, "link") or "").strip()
    if not title or not url:
        return None
    published = _entry_datetime(entry)
    snippet = clean_text(_get(entry, "summary") or _get(entry, "description"), max_length=800)
    language = str(_get(entry, "language") or default_language or "").strip() or None
    return Article(
        title=title,
        url=url,
        source=source_name,
        published_at=published,
        snippet=snippet or None,
        language=language,
        raw=dict(entry),
        reliability_score=reliability_score,
        ownership=ownership,
        bias_hint=bias_hint,
        category=category,
        source_type=source_type,
        source_url=source_url,
        source_tier=source_tier,
        source_role=source_role,  # type: ignore[arg-type]
        state_affiliated=state_affiliated,
        propaganda_risk=propaganda_risk,  # type: ignore[arg-type]
        editorial_context=editorial_context,
    )


def _entry_datetime(entry: Any) -> datetime | None:
    for attr in ("published", "updated", "created"):
        parsed = parse_datetime(_get(entry, attr))
        if parsed:
            return parsed
    return None


def _get(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)
