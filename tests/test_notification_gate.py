from __future__ import annotations

from src.llm_client import parse_llm_analysis
from src.models import Article, EventCluster, TopicConfig
from src.verification.report_quality import build_verification_report, notification_gate_decision
from tests.test_llm_schema import VALID_JSON


def test_social_only_reports_are_labelled_unconfirmed_but_can_notify():
    article = Article(
        "Unconfirmed policy signal",
        "https://x.com/example/status/1",
        "X",
        snippet="A social post claims a new policy is coming.",
        source_type="x",
        reliability_score=0.35,
    )
    cluster = EventCluster("c1", article.title, [article])
    topic = TopicConfig("Policy", True, "Prompt", ["policy"], social_enabled=True)
    analysis = parse_llm_analysis(VALID_JSON)

    report = build_verification_report(cluster, analysis)
    decision = notification_gate_decision(topic, report)

    assert report.social_only is True
    assert decision.should_notify is True
    assert decision.status == "unconfirmed"
    assert "social" in decision.user_label


def test_confidence_threshold_blocks_low_confidence_reports():
    article = Article("Blog rumor", "https://example.com/rumor", "Blog", source_role="blog", reliability_score=0.2)
    cluster = EventCluster("c1", article.title, [article])
    topic = TopicConfig("Policy", True, "Prompt", ["policy"], min_confidence_score=0.7)

    report = build_verification_report(cluster)
    decision = notification_gate_decision(topic, report)

    assert decision.should_notify is False
    assert decision.status == "low_confidence"
