from __future__ import annotations

from src.models import SelectedSource, SourceCandidate, TopicConfig

PRIMARY_SOURCE_TYPES = {"gov", "official", "sec", "company_ir", "github", "arxiv", "academic"}
SOCIAL_SOURCE_TYPES = {"x", "social"}


def rank_source_candidates(
    topic: TopicConfig,
    candidates: list[SourceCandidate],
    *,
    limit: int = 12,
) -> list[SelectedSource]:
    domains = set(topic.domains)
    ranked = [
        _selected_source(topic, candidate, domains)
        for candidate in candidates
        if _allowed_for_topic(topic, candidate, domains)
    ]
    ranked.sort(key=lambda item: item.priority, reverse=True)
    return ranked[:limit]


def _allowed_for_topic(topic: TopicConfig, candidate: SourceCandidate, domains: set[str]) -> bool:
    if candidate.source_type in SOCIAL_SOURCE_TYPES and not topic.social_enabled:
        return False
    if not domains:
        return True
    candidate_domains = set(candidate.domain_tags)
    if domains.intersection(candidate_domains):
        return True
    if "history" in domains:
        return candidate.source_type in {"academic", "website"} or "general_breaking_news" not in candidate_domains
    return False


def _selected_source(topic: TopicConfig, candidate: SourceCandidate, domains: set[str]) -> SelectedSource:
    score = 0
    reasons: list[str] = []
    risks: list[str] = []
    candidate_domains = set(candidate.domain_tags)
    if domains.intersection(candidate_domains):
        score += 35
        reasons.append("domain match")
    if candidate.enabled_by_default:
        score += 12
        reasons.append("enabled source")
    if candidate.source_type in PRIMARY_SOURCE_TYPES:
        score += 20
        reasons.append("primary or official source")
    if candidate.source_type == "arxiv" and domains.intersection(
        {"technology", "ai_industry", "science", "semiconductor"}
    ):
        score += 18
        reasons.append("research feed")
    if candidate.credibility_hint is not None:
        score += round(candidate.credibility_hint * 25)
        if candidate.credibility_hint >= 0.8:
            reasons.append("high credibility hint")
    if candidate.country_or_region and candidate.country_or_region in topic.preferred_regions:
        score += 10
        reasons.append("preferred region")
    if candidate.source_type in SOCIAL_SOURCE_TYPES:
        score -= 20
        risks.append("social media signal; requires corroboration")
    if candidate.requires_api_key:
        risks.append("requires API key")
    if "history" in domains and "general_breaking_news" in candidate_domains:
        score -= 25
        risks.append("breaking-news source is weak for historical topics")
    reason = ", ".join(reasons) if reasons else "broad topic coverage"
    expected = _expected_value(candidate, domains)
    return SelectedSource(
        candidate=candidate,
        reason=reason,
        expected_value=expected,
        risk="; ".join(risks) if risks else None,
        priority=score,
    )


def _expected_value(candidate: SourceCandidate, domains: set[str]) -> str:
    if candidate.source_type in PRIMARY_SOURCE_TYPES:
        return "primary evidence or official confirmation"
    if "finance" in domains or "public_companies" in domains:
        return "business impact and market context"
    if "politics" in domains or "geopolitics" in domains or "public_policy" in domains:
        return "policy context and cross-source comparison"
    if "history" in domains:
        return "stable background and reference context"
    return "relevant public topic coverage"
