from __future__ import annotations

from src.models import Article, SourceCredibility

SOCIAL_SOURCE_TYPES = {"x", "social", "tweet"}


def evaluate_source_credibility(article: Article) -> SourceCredibility:
    score = max(0.0, min(1.0, article.reliability_score))
    reasons: list[str] = []
    risks: list[str] = []
    if article.source_role in {"official", "company_ir"}:
        score += 0.12
        reasons.append("primary or official source")
    if article.source_tier == 1:
        score += 0.08
        reasons.append("tier 1 source")
    if article.source_type in SOCIAL_SOURCE_TYPES:
        score -= 0.25
        risks.append("social media signal")
    if article.source_role in {"aggregator", "blog"}:
        score -= 0.08
        risks.append("aggregator or low-context source")
    if article.propaganda_risk in {"medium", "high"}:
        score -= 0.08 if article.propaganda_risk == "medium" else 0.18
        risks.append(f"propaganda risk {article.propaganda_risk}")
    if article.confirmation_source_count > 1:
        score += min(0.12, 0.04 * article.confirmation_source_count)
        reasons.append("corroborated by multiple sources")
    bounded = max(0.0, min(1.0, score))
    return SourceCredibility(
        source_name=article.source,
        credibility_score=round(bounded, 2),
        confidence_level=_confidence_level(bounded),
        reasons=reasons,
        risks=risks,
    )


def _confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"
