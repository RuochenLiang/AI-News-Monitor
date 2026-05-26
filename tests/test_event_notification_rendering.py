from __future__ import annotations

from datetime import UTC, datetime

from src.event_clustering import cluster_event_articles
from src.event_synthesis import source_links_from_articles
from src.models import Alert, Article, LLMAnalysis, TopicConfig
from src.notifiers.base import format_alert_text


def test_event_notification_includes_timeline_source_links_and_group_count():
    article_one = Article(
        title="Official chip export notice",
        url="https://official.example/notice",
        source="Official Source",
        published_at=datetime(2026, 5, 25, tzinfo=UTC),
        snippet="Official notice published.",
        language="en",
        source_role="official",
    )
    article_two = Article(
        title="Industry reaction to chip export notice",
        url="https://trade.example/reaction",
        source="Trade Press",
        published_at=datetime(2026, 5, 26, tzinfo=UTC),
        snippet="Industry reacted.",
        language="en",
    )
    topic = TopicConfig("Export controls", True, "Track policy.", ["chip export notice"])
    cluster = cluster_event_articles([article_one, article_two], topic)[0]
    analysis = LLMAnalysis(
        relevance_score=95,
        is_actionable_alert=True,
        event_type="policy",
        summary="Two sources describe one chip export-control event.",
        why_it_matters="It may affect AI chip supply chains.",
        market_watch_suggestions=[],
        bullish_path="N/A",
        bearish_path="N/A",
        risk_notes="N/A",
        uncertainty_notes="Details may change.",
        source_reliability="high",
        recommended_user_action="research_further",
        notification_title="Chip export-control event",
        event_title="Chip export-control event",
        event_summary="Two sources describe one chip export-control event.",
        current_status="Official notice published; industry reaction ongoing.",
        timeline=cluster.timeline,
        key_facts=["Official notice was published.", "Industry reaction followed."],
        source_links=source_links_from_articles(cluster.articles),
        relation_reason=cluster.relation_reason,
        uncertainties=["Company-level impact is not yet confirmed."],
        suggested_actions=["Monitor official updates."],
        grouped_article_count=2,
    )
    alert = Alert("Export controls", cluster.primary_article, analysis, datetime.now(UTC), event_cluster=cluster)

    body = format_alert_text(alert, "en")

    assert "Grouped articles: 2" in body
    assert "Timeline:" in body
    assert "2026-05-25" in body
    assert "2026-05-26" in body
    assert "https://official.example/notice" in body
    assert "https://trade.example/reaction" in body
    assert "Why these articles are related:" in body
    assert "{" not in body


def test_event_notification_respects_topic_report_style_flags():
    article = Article(
        title="Official policy notice",
        url="https://official.example/notice",
        source="Official Source",
        published_at=datetime(2026, 5, 25, tzinfo=UTC),
        snippet="Official notice published.",
        language="en",
        source_role="official",
    )
    topic = TopicConfig("Policy", True, "Track policy.", ["policy"])
    cluster = cluster_event_articles([article], topic)[0]
    analysis = LLMAnalysis(
        relevance_score=95,
        is_actionable_alert=True,
        event_type="policy",
        summary="Official policy notice.",
        why_it_matters="It may affect compliance.",
        market_watch_suggestions=[],
        bullish_path="N/A",
        bearish_path="N/A",
        risk_notes="N/A",
        uncertainty_notes="Details may change.",
        source_reliability="high",
        recommended_user_action="research_further",
        notification_title="Policy notice",
        event_title="Policy notice",
        event_summary="Official policy notice.",
        current_status="Published.",
        timeline=cluster.timeline,
        key_facts=["Notice was published."],
        source_links=source_links_from_articles(cluster.articles),
        relation_reason=cluster.relation_reason,
        uncertainties=["Implementation details may change."],
        suggested_actions=["Monitor official updates."],
        report_include_timeline=False,
        report_include_user_action=False,
    )
    alert = Alert("Policy", cluster.primary_article, analysis, datetime.now(UTC), event_cluster=cluster)

    body = format_alert_text(alert, "en")

    assert "Timeline:" not in body
    assert "Suggested follow-up:" not in body
    assert "https://official.example/notice" in body
