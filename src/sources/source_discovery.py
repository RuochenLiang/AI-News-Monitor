from __future__ import annotations

from src.models import SelectedSource, SourceSettings, TopicConfig
from src.sources.source_ranker import rank_source_candidates
from src.sources.source_registry import source_registry

DOMAIN_KEYWORDS = {
    "technology": ["technology", "software", "api", "cloud", "chip", "semiconductor", "ai"],
    "ai_industry": ["openai", "llm", "model", "ai", "nvidia", "anthropic"],
    "finance": ["stock", "earnings", "market", "revenue", "finance", "investor"],
    "public_companies": ["sec", "public company", "investor relations", "earnings"],
    "politics": ["government", "president", "minister", "policy", "congress", "parliament"],
    "elections": ["election", "vote", "campaign", "ballot"],
    "geopolitics": ["china", "taiwan", "sanction", "trade", "export control", "defense"],
    "history": ["history", "archive", "historical", "museum"],
    "science": ["research", "paper", "journal", "preprint", "science"],
    "health": ["health", "medicine", "clinical", "disease"],
    "culture": ["culture", "film", "music", "art"],
    "public_policy": ["regulation", "agency", "rulemaking", "policy"],
    "local_news": ["local", "city", "county", "state"],
}


def classify_topic_domains(topic: TopicConfig) -> list[str]:
    explicit = [domain for domain in topic.domains if domain]
    if explicit:
        return explicit
    text = " ".join([topic.name, topic.prompt, " ".join(topic.keywords)]).casefold()
    domains = [domain for domain, markers in DOMAIN_KEYWORDS.items() if any(marker in text for marker in markers)]
    if not domains:
        return ["general_breaking_news"]
    return domains[:4]


def discover_sources_for_topic(
    topic: TopicConfig,
    settings: SourceSettings | None = None,
    *,
    limit: int = 12,
) -> list[SelectedSource]:
    topic_for_discovery = topic
    if not topic.domains:
        topic_for_discovery = TopicConfig(
            name=topic.name,
            enabled=topic.enabled,
            prompt=topic.prompt,
            keywords=topic.keywords,
            related_stocks=topic.related_stocks,
            output_language=topic.output_language,
            min_relevance_score=topic.min_relevance_score,
            poll_interval_seconds=topic.poll_interval_seconds,
            cooldown_minutes=topic.cooldown_minutes,
            official_rss_urls=topic.official_rss_urls,
            broad_search=topic.broad_search,
            id=topic.id,
            source_mode=topic.source_mode,
            domains=classify_topic_domains(topic),
            preferred_regions=topic.preferred_regions,
            social_enabled=topic.social_enabled,
            min_confidence_score=topic.min_confidence_score,
            report_include_timeline=topic.report_include_timeline,
            report_include_source_comparison=topic.report_include_source_comparison,
            report_include_user_action=topic.report_include_user_action,
        )
    return rank_source_candidates(topic_for_discovery, source_registry(settings), limit=limit)
