from __future__ import annotations

from src.llm_client import parse_llm_analysis
from src.models import Article, EventCluster, TopicConfig
from src.monitor import _apply_topic_report_style
from src.verification.report_quality import build_verification_report
from tests.test_llm_schema import VALID_JSON


def test_verification_report_includes_source_comparison_inputs():
    articles = [
        Article(
            "Official AI chip policy", "https://example.com/a", "Agency", reliability_score=0.9, source_role="official"
        ),
        Article(
            "Media confirms AI chip policy", "https://example.com/b", "Wire", reliability_score=0.8, source_role="wire"
        ),
    ]
    cluster = EventCluster("c1", "AI chip policy", articles)
    analysis = parse_llm_analysis(VALID_JSON)

    report = build_verification_report(cluster, analysis)

    assert report.confidence_score >= 0.75
    assert report.status == "verified"
    assert report.source_count == 2
    assert len(report.source_credibility) == 2


def test_verification_report_surfaces_contradictory_claim_risk():
    articles = [
        Article(
            "Company X confirmed a new AI accelerator.", "https://example.com/a", "Official", reliability_score=0.9
        ),
        Article(
            "Company X denied a new AI accelerator report.", "https://example.com/b", "Wire", reliability_score=0.8
        ),
    ]
    cluster = EventCluster("c1", "Company X accelerator", articles)

    report = build_verification_report(cluster)

    assert report.claims[0].contradicting_sources == ["Wire"]
    assert any("contradictory" in risk for risk in report.risks)


def test_report_style_can_hide_timeline_source_comparison_and_actions():
    topic = TopicConfig(
        "Policy",
        True,
        "Prompt",
        ["policy"],
        report_include_timeline=False,
        report_include_source_comparison=False,
        report_include_user_action=False,
    )
    analysis = parse_llm_analysis(VALID_JSON)
    analysis.source_comparison = [{"source": "Agency", "confidence": "high"}]

    _apply_topic_report_style(topic, analysis)

    assert analysis.timeline == []
    assert analysis.source_comparison == []
    assert analysis.suggested_actions == []
    assert analysis.report_include_timeline is False
    assert analysis.report_include_source_comparison is False
    assert analysis.report_include_user_action is False
