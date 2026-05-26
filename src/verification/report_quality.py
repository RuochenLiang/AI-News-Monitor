from __future__ import annotations

from src.models import (
    EventCluster,
    LLMAnalysis,
    NotificationGateDecision,
    TopicConfig,
    VerificationReport,
)
from src.source_reliability import source_owner_key
from src.verification.claim_extraction import extract_claims
from src.verification.corroboration import corroborate_claims
from src.verification.credibility import evaluate_source_credibility

SOCIAL_SOURCE_TYPES = {"x", "social", "tweet"}


def build_verification_report(cluster: EventCluster, analysis: LLMAnalysis | None = None) -> VerificationReport:
    articles = cluster.articles
    source_credibility = [evaluate_source_credibility(article) for article in articles]
    source_count = len({article.source for article in articles})
    independent_source_count = len({source_owner_key(article) or article.source for article in articles})
    social_only = bool(articles) and all(
        (article.source_type or "").casefold() in SOCIAL_SOURCE_TYPES for article in articles
    )
    claims = corroborate_claims([claim for article in articles for claim in extract_claims(article)])
    contradictory_claims = [claim for claim in claims if claim.contradicting_sources]
    base = _average([item.credibility_score for item in source_credibility], default=0.0)
    if source_count > 1:
        base += min(0.18, 0.06 * (source_count - 1))
    if independent_source_count > 1:
        base += min(0.12, 0.04 * (independent_source_count - 1))
    if analysis:
        base = (base * 0.75) + (_reliability_hint(analysis.source_reliability) * 0.25)
    if social_only:
        base = min(base, 0.45)
    if contradictory_claims:
        base = max(0.0, base - 0.12)
    confidence_score = round(max(0.0, min(1.0, base)), 2)
    status = _status(confidence_score, source_count, social_only)
    reasons = _reasons(status, source_count, independent_source_count)
    risks = ["social media only; requires corroboration"] if social_only else []
    if contradictory_claims:
        risks.append("contradictory claims found; review source comparison")
    return VerificationReport(
        status=status,
        confidence_score=confidence_score,
        source_credibility=source_credibility,
        claims=claims,
        reasons=reasons,
        risks=risks,
        source_count=source_count,
        independent_source_count=independent_source_count,
        social_only=social_only,
    )


def notification_gate_decision(topic: TopicConfig, report: VerificationReport) -> NotificationGateDecision:
    threshold = topic.min_confidence_score or 0.0
    if report.status == "low_confidence" or report.confidence_score < threshold:
        return NotificationGateDecision(
            should_notify=False,
            status="low_confidence",
            confidence_score=report.confidence_score,
            reason="Verification confidence is below the topic threshold.",
            user_label="low-confidence",
        )
    if report.social_only:
        return NotificationGateDecision(
            should_notify=True,
            status="unconfirmed",
            confidence_score=report.confidence_score,
            reason="Only social media evidence is available; label as unconfirmed.",
            user_label="unconfirmed social-media signal",
        )
    return NotificationGateDecision(
        should_notify=True,
        status=report.status,
        confidence_score=report.confidence_score,
        reason="Verification gate passed.",
        user_label=report.status.replace("_", "-"),
    )


def _status(confidence_score: float, source_count: int, social_only: bool) -> str:
    if social_only:
        return "unconfirmed"
    if confidence_score >= 0.75 and source_count >= 1:
        return "verified"
    if confidence_score >= 0.5:
        return "developing"
    return "low_confidence"


def _reasons(status: str, source_count: int, independent_source_count: int) -> list[str]:
    reasons = [f"verification status: {status}"]
    if source_count > 1:
        reasons.append(f"{source_count} sources mention the event")
    if independent_source_count > 1:
        reasons.append(f"{independent_source_count} independent source owners")
    return reasons


def _reliability_hint(value: str) -> float:
    return {"high": 0.85, "medium": 0.62, "low": 0.35}.get(str(value), 0.5)


def _average(values: list[float], *, default: float) -> float:
    return sum(values) / len(values) if values else default
