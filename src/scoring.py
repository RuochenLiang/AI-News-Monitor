from __future__ import annotations

from datetime import timedelta

from src.models import Article, QualitySettings, TopicConfig
from src.source_reliability import confirmation_key, source_owner_key
from src.storage import SQLiteStore
from src.utils.text_utils import keyword_matches
from src.utils.time_utils import utc_now
from src.utils.url_utils import is_valid_http_url


def topic_threshold(topic: TopicConfig, default_threshold: int) -> int:
    return topic.min_relevance_score if topic.min_relevance_score is not None else default_threshold


def cooldown_allows_alert(store: SQLiteStore, topic: TopicConfig) -> bool:
    if not topic.cooldown_minutes:
        return True
    latest = store.latest_alert_for_topic(topic.name)
    if not latest:
        return True
    return utc_now() - latest >= timedelta(minutes=topic.cooldown_minutes)


def hourly_rate_limit_allows_alert(store: SQLiteStore, max_alerts_per_hour: int) -> bool:
    since = utc_now() - timedelta(hours=1)
    return store.alert_count_since(since) < max_alerts_per_hour


def compute_article_priority(
    article: Article,
    topic: TopicConfig,
    quality: QualitySettings | None = None,
    *,
    now=None,
    cluster_sizes: dict[str, int] | None = None,
    confirmation_groups: dict[str, list[Article]] | None = None,
    preferred_language: str | None = None,
) -> float:
    quality = quality or QualitySettings()
    now = now or utc_now()
    keyword = _keyword_score(article, topic)
    recency = _recency_score(article, now)
    reliability = _bounded(article.reliability_score)
    tier_boost = _source_tier_boost(article)
    official_boost = quality.official_source_boost if _is_official_source(article) else 0.0
    company_ir_boost = quality.company_ir_boost if _is_company_ir_source(article) else 0.0
    confirmation = _confirmation_context(article, confirmation_groups)
    cluster_boost = quality.multi_source_confirmation_boost if confirmation["source_count"] > 1 else 0.0
    independent_bonus = min(0.15, max(0, confirmation["independent_count"] - 1) * quality.independent_source_bonus)
    same_owner_penalty = (
        quality.same_owner_confirmation_penalty
        if confirmation["source_count"] > 1 and confirmation["independent_count"] < confirmation["source_count"]
        else 0.0
    )
    official_media_bonus = 0.04 if confirmation["official_and_media"] else 0.0
    cluster_strength_boost = min(
        quality.event_cluster_strength_boost * max(0, _cluster_size(article, cluster_sizes) - 1), 0.15
    )
    whitelist_boost = quality.whitelist_boost if _source_matches(article, quality.whitelist_sources) else 0.0
    low_quality_penalty = quality.low_quality_source_penalty if _is_low_quality_source(article) else 0.0
    propaganda_penalty = _propaganda_penalty(article)
    duplicate_penalty = quality.duplicate_rewrite_penalty if _looks_rewritten_duplicate(article) else 0.0
    language_boost = 0.04 if preferred_language and article.language == preferred_language else 0.0
    original_link_boost = 0.03 if is_valid_http_url(article.url) else 0.0
    category_boost = quality.category_priority.get(article.category or "", 0.0)
    score = (
        (keyword * 0.38)
        + (recency * 0.28)
        + (reliability * 0.28)
        + tier_boost
        + official_boost
        + company_ir_boost
        + cluster_boost
        + independent_bonus
        + official_media_bonus
        + cluster_strength_boost
        + whitelist_boost
        + language_boost
        + original_link_boost
        + category_boost
        - low_quality_penalty
        - same_owner_penalty
        - propaganda_penalty
        - duplicate_penalty
    )
    article.confirmation_summary = str(confirmation["summary"] or "") or None
    article.confirmation_source_count = int(confirmation["source_count"])
    article.independent_source_count = int(confirmation["independent_count"])
    article.match_reason = _match_reason(article, topic)
    article.selection_reason = _selection_reason(
        article,
        keyword,
        recency,
        reliability,
        tier_boost,
        official_boost,
        company_ir_boost,
        cluster_boost,
        independent_bonus,
        official_media_bonus,
        same_owner_penalty,
        cluster_strength_boost,
        whitelist_boost,
        low_quality_penalty,
        propaganda_penalty,
        duplicate_penalty,
        category_boost,
    )
    return round(score * 100, 2)


def rank_articles(
    articles: list[Article],
    topic: TopicConfig,
    quality: QualitySettings | None = None,
    *,
    preferred_language: str | None = None,
) -> list[Article]:
    quality = quality or QualitySettings()
    cluster_sizes = _cluster_sizes(articles)
    confirmation_groups = _confirmation_groups(articles)
    ranked: list[Article] = []
    for article in articles:
        if quality.blacklist_exclude and _source_matches(article, quality.blacklist_sources):
            article.ranking_score = 0
            article.selection_reason = "Excluded by source blacklist."
            continue
        article.ranking_score = compute_article_priority(
            article,
            topic,
            quality,
            cluster_sizes=cluster_sizes,
            confirmation_groups=confirmation_groups,
            preferred_language=preferred_language,
        )
        ranked.append(article)
    return sorted(
        ranked,
        key=lambda item: (item.ranking_score, item.published_at or utc_now()),
        reverse=True,
    )


def _keyword_score(article: Article, topic: TopicConfig) -> float:
    if topic.broad_search:
        article.matched_keywords = []
        return 0.65
    combined = f"{article.title}\n{article.snippet or ''}".casefold()
    keywords = [keyword.strip().casefold() for keyword in topic.keywords if keyword.strip()]
    if not keywords:
        article.matched_keywords = []
        return 0.0
    exact = [keyword for keyword in keywords if keyword in combined]
    article.matched_keywords = exact
    exact_matches = len(exact)
    if exact_matches:
        return min(1.0, 0.35 + (exact_matches / max(1, min(len(keywords), 5))) * 0.65)
    return 0.25 if keyword_matches(combined, keywords) else 0.0


def _recency_score(article: Article, now) -> float:
    if not article.published_at:
        return 0.4
    age_hours = max(0.0, (now - article.published_at).total_seconds() / 3600)
    if age_hours <= 1:
        return 1.0
    if age_hours <= 6:
        return 0.85
    if age_hours <= 24:
        return 0.65
    if age_hours <= 72:
        return 0.35
    return 0.1


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _is_official_source(article: Article) -> bool:
    if article.source_role == "official":
        return True
    text = " ".join(
        item
        for item in [
            article.source,
            article.category or "",
            article.source_type or "",
            article.ownership or "",
        ]
        if item
    ).casefold()
    return any(marker in text for marker in ["official", "government", "gov", "company ir", "press release"])


def _is_low_quality_source(article: Article) -> bool:
    if article.source_tier == 4 or article.source_role in {"aggregator", "blog"}:
        return True
    source = article.source.casefold()
    aggregator = any(marker in source for marker in ["aggregator", "google news", "yahoo finance", "gdelt"])
    return aggregator or article.reliability_score < 0.35


def _is_company_ir_source(article: Article) -> bool:
    if article.source_role == "company_ir":
        return True
    text = " ".join(
        item
        for item in [
            article.source,
            article.category or "",
            article.source_type or "",
            article.ownership or "",
            article.url,
        ]
        if item
    ).casefold()
    return any(marker in text for marker in ["company ir", "investor", "newsroom", "press release", "ir."])


def _looks_rewritten_duplicate(article: Article) -> bool:
    text = " ".join([article.source, article.title, article.snippet or "", article.url]).casefold()
    return any(marker in text for marker in ["rewritten", "republished", "syndicated", "via ", "press release roundup"])


def _source_matches(article: Article, patterns: list[str]) -> bool:
    haystack = "\n".join([article.source, article.url, article.ownership or "", article.category or ""]).casefold()
    return any(pattern.strip().casefold() in haystack for pattern in patterns if pattern.strip())


def _cluster_sizes(articles: list[Article]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for article in articles:
        key = article.event_cluster_id or _event_key(article)
        sizes[key] = sizes.get(key, 0) + 1
    return sizes


def _confirmation_groups(articles: list[Article]) -> dict[str, list[Article]]:
    groups: dict[str, list[Article]] = {}
    for article in articles:
        groups.setdefault(article.event_cluster_id or confirmation_key(article), []).append(article)
    return groups


def _confirmation_context(article: Article, groups: dict[str, list[Article]] | None) -> dict[str, object]:
    if not groups:
        return {
            "source_count": 1,
            "independent_count": 1,
            "official_and_media": False,
            "summary": "",
        }
    items = groups.get(article.event_cluster_id or confirmation_key(article), [article])
    source_names = {item.source for item in items}
    owners = {source_owner_key(item) for item in items if source_owner_key(item)}
    roles = {item.source_role for item in items}
    official_or_primary = bool(roles.intersection({"official", "company_ir"}))
    media = bool(roles.intersection({"wire", "major_media", "niche_media"}))
    source_count = max(1, len(source_names))
    independent_count = max(1, len(owners or source_names))
    summary = ""
    if source_count > 1:
        official_count = len([item for item in items if item.source_role in {"official", "company_ir"}])
        major_count = len([item for item in items if item.source_role in {"wire", "major_media", "niche_media"}])
        parts = []
        if official_count:
            parts.append(f"{official_count} primary/official source(s)")
        if major_count:
            parts.append(f"{major_count} media source(s)")
        summary = f"Confirmed by {source_count} sources: {', '.join(parts) or ', '.join(sorted(source_names)[:4])}."
    return {
        "source_count": source_count,
        "independent_count": independent_count,
        "official_and_media": official_or_primary and media and independent_count > 1,
        "summary": summary,
    }


def _cluster_size(article: Article, cluster_sizes: dict[str, int] | None) -> int:
    if not cluster_sizes:
        return 1
    return cluster_sizes.get(article.event_cluster_id or _event_key(article), 1)


def _event_key(article: Article) -> str:
    words = [
        word.strip(".,:;!?()[]{}\"'").casefold()
        for word in article.title.split()
        if len(word.strip(".,:;!?()[]{}\"'")) > 3
    ]
    return " ".join(words[:8]) or article.url.casefold()


def _source_tier_boost(article: Article) -> float:
    return {1: 0.10, 2: 0.05, 3: 0.0, 4: -0.06}.get(int(article.source_tier or 4), -0.06)


def _propaganda_penalty(article: Article) -> float:
    risk = article.propaganda_risk
    if risk == "high":
        return 0.08
    if risk == "medium":
        return 0.04
    return 0.0


def _match_reason(article: Article, topic: TopicConfig) -> str:
    if topic.broad_search:
        return "Topic uses broad search; ranked by recency, reliability, and source quality."
    if article.matched_keywords:
        return "Matched keywords: " + ", ".join(article.matched_keywords)
    return "Weak semantic/topic match; retained for ranking."


def _selection_reason(
    article: Article,
    keyword: float,
    recency: float,
    reliability: float,
    tier_boost: float,
    official_boost: float,
    company_ir_boost: float,
    cluster_boost: float,
    independent_bonus: float,
    official_media_bonus: float,
    same_owner_penalty: float,
    cluster_strength_boost: float,
    whitelist_boost: float,
    low_quality_penalty: float,
    propaganda_penalty: float,
    duplicate_penalty: float,
    category_boost: float,
) -> str:
    parts = [
        f"keyword {keyword:.2f}",
        f"recency {recency:.2f}",
        f"reliability {reliability:.2f}",
        f"tier {article.source_tier} {tier_boost:+.2f}",
    ]
    if official_boost:
        parts.append(f"official/source boost +{official_boost:.2f}")
    if company_ir_boost:
        parts.append(f"company IR boost +{company_ir_boost:.2f}")
    if cluster_boost:
        parts.append(f"multi-source boost +{cluster_boost:.2f}")
    if independent_bonus:
        parts.append(f"independent source bonus +{independent_bonus:.2f}")
    if official_media_bonus:
        parts.append(f"official/media confirmation +{official_media_bonus:.2f}")
    if cluster_strength_boost:
        parts.append(f"event cluster strength +{cluster_strength_boost:.2f}")
    if whitelist_boost:
        parts.append(f"whitelist boost +{whitelist_boost:.2f}")
    if category_boost:
        parts.append(f"category priority {category_boost:+.2f}")
    if low_quality_penalty:
        parts.append(f"low-quality penalty -{low_quality_penalty:.2f}")
    if same_owner_penalty:
        parts.append(f"same-owner confirmation penalty -{same_owner_penalty:.2f}")
    if propaganda_penalty:
        parts.append(f"propaganda risk penalty -{propaganda_penalty:.2f}")
    if duplicate_penalty:
        parts.append(f"duplicate/rewrite penalty -{duplicate_penalty:.2f}")
    if article.confirmation_summary:
        parts.append(article.confirmation_summary)
    if article.bias_hint:
        parts.append(f"context: {article.bias_hint}")
    return "; ".join(parts)
