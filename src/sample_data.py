from __future__ import annotations

from datetime import UTC, datetime

from src.models import Alert, Article, LLMAnalysis, MarketWatchSuggestion


def sample_alert() -> Alert:
    analysis = LLMAnalysis(
        relevance_score=91,
        is_actionable_alert=True,
        event_type="test",
        summary="This is an AI News Monitor test notification.",
        why_it_matters="It confirms that the notification channel can deliver messages.",
        market_watch_suggestions=[
            MarketWatchSuggestion(
                "TEST", "Test topic", "unclear", "Test notifications are not real market events.", "low"
            )
        ],
        bullish_path="None; this is a test message.",
        bearish_path="None; this is a test message.",
        risk_notes="This test message has no investment meaning.",
        uncertainty_notes="This test message does not contain real news.",
        source_reliability="low",
        recommended_user_action="watch_only",
        notification_title="AI News Monitor Test Notification",
    )
    article = Article(
        title="AI News Monitor Test Notification",
        url="https://example.com/ai-news-monitor-test",
        source="AI News Monitor",
        published_at=datetime.now(UTC),
        snippet="Test notification",
        language="en",
    )
    return Alert("Test topic", article, analysis, datetime.now(UTC), mode="full_analysis", output_language="en")
