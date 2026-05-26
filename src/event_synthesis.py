from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.models import Article, EventCluster, SourceLink, TimelineItem
from src.utils.text_utils import clean_text

ISO_DATE_RE = re.compile(r"\b((?:19|20)\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b")
MONTH_DATE_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.?\s+([0-2]?\d|3[01]),?\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def build_timeline(articles: list[Article]) -> list[TimelineItem]:
    items: list[TimelineItem] = []
    for article in articles:
        items.extend(_mentioned_timeline_items(article))
        items.append(_timeline_item(article))
    return sorted(items, key=_timeline_sort_key)


def source_links_from_articles(articles: list[Article]) -> list[SourceLink]:
    links: list[SourceLink] = []
    seen: set[str] = set()
    for article in articles:
        if article.url in seen:
            continue
        seen.add(article.url)
        links.append(
            SourceLink(
                title=article.title,
                url=article.url,
                publisher=article.source,
                published_at=article.published_at.isoformat() if article.published_at else "",
            )
        )
    return links


def cluster_to_llm_payload(cluster: EventCluster) -> dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "title": cluster.title,
        "article_count": cluster.article_count,
        "relation_reason": cluster.relation_reason,
        "confidence": cluster.confidence,
        "entities": cluster.entities,
        "earliest_published_at": cluster.earliest_published_at.isoformat() if cluster.earliest_published_at else None,
        "latest_published_at": cluster.latest_published_at.isoformat() if cluster.latest_published_at else None,
        "timeline_seed": [item.to_dict() for item in cluster.timeline],
        "articles": [_article_payload(article) for article in cluster.articles],
    }


def cluster_status_payload(cluster: EventCluster) -> dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "title": cluster.title,
        "article_count": cluster.article_count,
        "latest_update_time": cluster.latest_published_at,
        "relation_reason": cluster.relation_reason,
        "confidence": cluster.confidence,
        "entities": cluster.entities[:8],
        "timeline_preview": [item.to_dict() for item in cluster.timeline[:3]],
        "sources": [link.to_dict() for link in source_links_from_articles(cluster.articles)],
    }


def _timeline_item(article: Article) -> TimelineItem:
    published = article.published_at
    source_label = (
        "Official source published" if article.source_role in {"official", "company_ir"} else "Article published"
    )
    if published:
        description = clean_text(
            f"Publication-time based: {article.title}. {article.snippet or ''}",
            max_length=220,
        )
        return TimelineItem(
            date=published.date().isoformat(),
            time=_time_text(published),
            label=source_label,
            description=description,
            source_title=article.title,
            source_url=article.url,
            confidence=0.75 if article.source_role in {"official", "company_ir"} else 0.6,
        )
    return TimelineItem(
        date="unknown",
        time=None,
        label="Publication time unavailable",
        description=clean_text(
            f"Publication time unavailable; exact event date is not provided by this source. {article.title}. "
            f"{article.snippet or ''}",
            max_length=220,
        ),
        source_title=article.title,
        source_url=article.url,
        confidence=0.25,
    )


def _mentioned_timeline_items(article: Article) -> list[TimelineItem]:
    text = clean_text(f"{article.title}. {article.snippet or ''}", max_length=1000)
    items: list[TimelineItem] = []
    seen_dates: set[str] = set()
    for match in ISO_DATE_RE.finditer(text):
        date_text = match.group(0)
        date = _valid_iso_date(date_text)
        if date and date not in seen_dates:
            seen_dates.add(date)
            items.append(_mentioned_timeline_item(article, date, date_text))
    for match in MONTH_DATE_RE.finditer(text):
        date = _month_date_to_iso(match.group(1), match.group(2), match.group(3))
        if date and date not in seen_dates:
            seen_dates.add(date)
            items.append(_mentioned_timeline_item(article, date, match.group(0)))
    return items


def _mentioned_timeline_item(article: Article, date: str, date_text: str) -> TimelineItem:
    source_label = (
        "Official source-mentioned date"
        if article.source_role in {"official", "company_ir"}
        else "Source-mentioned date"
    )
    description = clean_text(
        f"Source-mentioned date: {date_text}. {article.title}. {article.snippet or ''}",
        max_length=220,
    )
    return TimelineItem(
        date=date,
        time=None,
        label=source_label,
        description=description,
        source_title=article.title,
        source_url=article.url,
        confidence=0.7 if article.source_role in {"official", "company_ir"} else 0.55,
    )


def _valid_iso_date(value: str) -> str | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _month_date_to_iso(month: str, day: str, year: str) -> str | None:
    month_number = MONTHS.get(month.rstrip(".").casefold())
    if not month_number:
        return None
    try:
        return datetime(int(year), month_number, int(day)).date().isoformat()
    except ValueError:
        return None


def _article_payload(article: Article) -> dict[str, Any]:
    return {
        "title": article.title,
        "snippet": article.snippet,
        "source": article.source,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "url": article.url,
        "language": article.language,
        "translated_title": article.translated_title,
        "translated_snippet": article.translated_snippet,
        "short_summary": article.short_summary,
        "source_reliability_score": article.reliability_score,
        "source_ownership": article.ownership,
        "source_bias_hint": article.bias_hint,
        "source_role": article.source_role,
        "source_tier": article.source_tier,
        "ranking_score": article.ranking_score,
        "matched_keywords": article.matched_keywords,
        "bias_context": (article.raw or {}).get("bias_summary") if article.raw else None,
    }


def _timeline_sort_key(item: TimelineItem) -> tuple[int, str, str]:
    if item.date == "unknown":
        return (1, "9999-99-99", item.time or "")
    return (0, item.date, item.time or "")


def _time_text(value: datetime) -> str | None:
    if value.hour == 0 and value.minute == 0 and value.second == 0:
        return None
    return value.strftime("%H:%M")
