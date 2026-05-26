from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlparse

from src.event_synthesis import build_timeline
from src.models import Article, EventCluster, TopicConfig
from src.utils.text_utils import clean_text
from src.utils.url_utils import normalize_url

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9&.+/-]{1,}|[\u4e00-\u9fff]{2,}")
ENTITY_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9&.+-]{1,}|[A-Z]{2,})\b")
STOPWORDS = {
    "about",
    "after",
    "again",
    "amid",
    "and",
    "are",
    "before",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "its",
    "may",
    "new",
    "not",
    "of",
    "on",
    "over",
    "said",
    "says",
    "the",
    "this",
    "that",
    "their",
    "they",
    "to",
    "update",
    "us",
    "we",
    "will",
    "with",
    "you",
    "your",
}
GENERIC_EVENT_TERMS = STOPWORDS | {
    "ai",
    "article",
    "breaking",
    "exclusive",
    "latest",
    "news",
    "report",
    "reports",
    "story",
}
ENTITY_STOPWORDS = {
    "A",
    "AI",
    "An",
    "And",
    "Apply",
    "Before",
    "Everyone",
    "For",
    "From",
    "In",
    "May",
    "Of",
    "On",
    "The",
    "This",
    "To",
    "US",
    "We",
    "With",
}


def cluster_event_articles(articles: list[Article], topic: TopicConfig | None = None) -> list[EventCluster]:
    if not articles:
        return []
    profiles = [_ArticleProfile(article, topic) for article in articles]
    parent = list(range(len(profiles)))
    for left_index, left in enumerate(profiles):
        for right_index in range(left_index + 1, len(profiles)):
            right = profiles[right_index]
            score = _relation_score(left, right)
            if score >= 0.58:
                _union(parent, left_index, right_index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(profiles)):
        groups[_find(parent, index)].append(index)

    clusters = [_build_cluster([profiles[index] for index in indexes], topic) for indexes in groups.values()]
    return sorted(clusters, key=_cluster_sort_key, reverse=True)


class _ArticleProfile:
    def __init__(self, article: Article, topic: TopicConfig | None):
        self.article = article
        combined = clean_text(f"{article.title} {article.snippet or ''}")
        self.tokens = _important_tokens(combined)
        self.entities = _entities(combined, topic)
        self.domain = _domain(article.url)
        self.topic_hits = _topic_hits(combined, article, topic)


def _build_cluster(profiles: list[_ArticleProfile], topic: TopicConfig | None) -> EventCluster:
    articles = sorted(
        [profile.article for profile in profiles],
        key=lambda item: (item.published_at is None, item.published_at, item.ranking_score),
    )
    representative = max(
        articles,
        key=lambda item: (
            item.reliability_score,
            item.ranking_score,
            item.published_at.isoformat() if item.published_at else "",
        ),
    )
    published = [article.published_at for article in articles if article.published_at]
    entities = sorted(set().union(*(profile.entities for profile in profiles)))
    shared_terms = _shared_terms(profiles)
    confidence = _cluster_confidence(profiles)
    relation_reason = _relation_reason(profiles, shared_terms, confidence)
    cluster_id = _cluster_id(articles)
    for article in articles:
        article.event_cluster_id = cluster_id
        if not article.match_reason and relation_reason:
            article.match_reason = relation_reason
    return EventCluster(
        cluster_id=cluster_id,
        title=representative.title,
        articles=articles,
        topics=[topic.name] if topic else [],
        entities=entities[:12],
        earliest_published_at=min(published) if published else None,
        latest_published_at=max(published) if published else None,
        confidence=confidence,
        relation_reason=relation_reason,
        timeline=build_timeline(articles),
    )


def _relation_score(left: _ArticleProfile, right: _ArticleProfile) -> float:
    token_overlap = _jaccard(left.tokens, right.tokens)
    shared_entities = _meaningful_terms(left.entities & right.entities)
    shared_topic_hits = _meaningful_terms(left.topic_hits & right.topic_hits)
    score = 0.0
    if token_overlap >= 0.35:
        score += 0.35
    elif token_overlap >= 0.22:
        score += 0.25
    if shared_topic_hits:
        score += 0.25
    if shared_entities:
        score += 0.2
    if left.domain and left.domain == right.domain:
        score += 0.1
    if _time_proximity(left.article, right.article):
        score += 0.12
    if left.article.category and left.article.category == right.article.category:
        score += 0.06
    if not (shared_entities or shared_topic_hits or token_overlap >= 0.22):
        return 0.0
    return min(score, 1.0)


def _cluster_confidence(profiles: list[_ArticleProfile]) -> float:
    if len(profiles) == 1:
        return 0.55
    pair_scores: list[float] = []
    for left_index, left in enumerate(profiles):
        for right in profiles[left_index + 1 :]:
            pair_scores.append(_relation_score(left, right))
    if not pair_scores:
        return 0.55
    source_bonus = min(len({profile.domain or profile.article.source for profile in profiles}) * 0.03, 0.12)
    return round(min(0.98, max(pair_scores) + source_bonus), 2)


def _relation_reason(profiles: list[_ArticleProfile], shared_terms: set[str], confidence: float) -> str:
    if len(profiles) == 1:
        return "Single source event cluster; no related articles were available in this cycle."
    terms = ", ".join(sorted(shared_terms)[:8])
    domains = len({profile.domain or profile.article.source for profile in profiles})
    if terms:
        return (
            f"Grouped because {len(profiles)} articles share event terms/entities ({terms}) "
            f"within a close publication window across {domains} source(s). Confidence {confidence:.2f}."
        )
    return (
        f"Grouped because {len(profiles)} articles have overlapping topic signals "
        f"within a close publication window across {domains} source(s). Confidence {confidence:.2f}."
    )


def _important_tokens(text: str) -> set[str]:
    tokens = set()
    normalized_text = text.replace("-", " ").replace("/", " ")
    for raw in TOKEN_RE.findall(normalized_text):
        token = raw.strip(" -_/.,:;()[]{}\"'").casefold()
        if len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        if len(token) < 2 or token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def _entities(text: str, topic: TopicConfig | None) -> set[str]:
    entities = {item.strip() for item in ENTITY_RE.findall(text) if len(item.strip()) >= 2}
    entities = {
        item for item in entities if item not in ENTITY_STOPWORDS and item.casefold() not in GENERIC_EVENT_TERMS
    }
    if topic:
        lowered = text.casefold()
        for keyword in topic.keywords:
            clean = clean_text(keyword)
            if clean and len(clean) >= 2 and clean.casefold() in lowered and _is_meaningful_relation_term(clean):
                entities.add(clean)
    return entities


def _topic_hits(text: str, article: Article, topic: TopicConfig | None) -> set[str]:
    hits = set(article.matched_keywords)
    if not topic:
        return {clean_text(item).casefold() for item in hits if clean_text(item)}
    lowered = text.casefold()
    for keyword in topic.keywords:
        clean = clean_text(keyword)
        if clean and clean.casefold() in lowered:
            hits.add(clean)
    return {clean_text(item).casefold() for item in hits if clean_text(item)}


def _shared_terms(profiles: list[_ArticleProfile]) -> set[str]:
    shared: set[str] = set()
    for left_index, left in enumerate(profiles):
        for right in profiles[left_index + 1 :]:
            shared.update(_meaningful_terms(left.entities & right.entities))
            shared.update(_meaningful_terms(left.topic_hits & right.topic_hits))
            shared.update(_meaningful_terms((left.tokens & right.tokens) - STOPWORDS))
    return shared


def _meaningful_terms(terms: set[str]) -> set[str]:
    return {term for term in terms if _is_meaningful_relation_term(term)}


def _is_meaningful_relation_term(term: str) -> bool:
    normalized = clean_text(term).casefold()
    if not normalized or normalized in GENERIC_EVENT_TERMS:
        return False
    if len(normalized) <= 2:
        return False
    return True


def _time_proximity(left: Article, right: Article) -> bool:
    if not left.published_at or not right.published_at:
        return True
    return abs(left.published_at - right.published_at) <= timedelta(hours=96)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.casefold()
    return host[4:] if host.startswith("www.") else host


def _cluster_id(articles: list[Article]) -> str:
    values = sorted(normalize_url(article.url) or article.title for article in articles)
    digest = hashlib.sha1("|".join(values).encode("utf-8")).hexdigest()[:12]
    return f"event-{digest}"


def _cluster_sort_key(cluster: EventCluster) -> tuple[float, int, str]:
    latest = cluster.latest_published_at.isoformat() if cluster.latest_published_at else ""
    return (cluster.confidence, cluster.article_count, latest)


def _find(parent: list[int], index: int) -> int:
    while parent[index] != index:
        parent[index] = parent[parent[index]]
        index = parent[index]
    return index


def _union(parent: list[int], left: int, right: int) -> None:
    left_root = _find(parent, left)
    right_root = _find(parent, right)
    if left_root != right_root:
        parent[right_root] = left_root
