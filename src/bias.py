from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.models import Article

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "as",
    "by",
    "from",
    "about",
    "after",
    "before",
    "says",
    "said",
    "news",
}


@dataclass
class EventCluster:
    id: str
    articles: list[Article]

    @property
    def sources(self) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for article in self.articles:
            if article.source not in seen:
                seen.add(article.source)
                names.append(article.source)
        return names


def cluster_articles(articles: list[Article], min_cluster_size: int = 2) -> list[EventCluster]:
    buckets: dict[str, list[Article]] = {}
    for article in articles:
        key = _cluster_key(article)
        buckets.setdefault(key, []).append(article)
    clusters: list[EventCluster] = []
    for key, items in buckets.items():
        if len(items) >= min_cluster_size:
            cluster_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
            for article in items:
                article.event_cluster_id = cluster_id
            clusters.append(EventCluster(cluster_id, items))
    return clusters


def annotate_bias_context(articles: list[Article], enabled: bool, mode: str, min_cluster_size: int = 2) -> None:
    if not enabled:
        return
    source_context = "\n".join(_source_line(article) for article in articles)
    for article in articles:
        raw = dict(article.raw or {})
        raw["source_context"] = _source_line(article)
        if mode == "single":
            raw["bias_summary"] = (
                "Single-source mode: compare this report with other sources before acting.\n" f"{raw['source_context']}"
            )
        article.raw = raw
    if mode != "cluster":
        return
    for cluster in cluster_articles(articles, min_cluster_size):
        summary = comparative_summary(cluster)
        for article in cluster.articles:
            raw = dict(article.raw or {})
            raw["bias_summary"] = summary
            raw["cluster_sources"] = cluster.sources
            article.raw = raw
    if source_context:
        for article in articles:
            raw = dict(article.raw or {})
            raw.setdefault("all_candidate_source_context", source_context)
            article.raw = raw


def comparative_summary(cluster: EventCluster) -> str:
    lines = [
        f"Cross-source cluster ({len(cluster.articles)} reports): {', '.join(cluster.sources)}.",
        "Compare wording, ownership, and omitted details before treating this as confirmed.",
    ]
    for article in cluster.articles[:5]:
        lines.append(f"- {article.source}: {article.title} ({article.bias_hint or 'bias unknown'})")
    return "\n".join(lines)


def _source_line(article: Article) -> str:
    parts = [article.source, f"reliability={article.reliability_score:.2f}"]
    if article.ownership:
        parts.append(f"owner={article.ownership}")
    if article.bias_hint:
        parts.append(f"bias={article.bias_hint}")
    return " | ".join(parts)


def _cluster_key(article: Article) -> str:
    title = article.title.casefold()
    tokens = [token for token in re.findall(r"[\w\u4e00-\u9fff]+", title) if token not in STOPWORDS]
    if not tokens:
        return title[:80]
    important = sorted(tokens[:10])
    day = article.published_at.date().isoformat() if article.published_at else ""
    return f"{day}:{' '.join(important[:8])}"
