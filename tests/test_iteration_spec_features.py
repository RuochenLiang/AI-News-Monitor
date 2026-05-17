from __future__ import annotations

from pathlib import Path

from src.config import parse_config
from src.models import AppConfig, Article, NotificationResult, NotificationRoutingSettings, QualitySettings, TopicConfig
from src.monitor import NewsMonitor, build_sources
from src.notifiers.base import format_alert_text
from src.sample_data import sample_alert
from src.scoring import rank_articles
from src.sources.library import SOURCE_LIBRARY_CATEGORIES, default_source_library, detect_feed_metadata
from src.storage import SQLiteStore
from src.utils.time_utils import utc_now


def test_fast_alert_omits_full_analysis_sections():
    alert = sample_alert()
    alert.mode = "fast"
    alert.output_language = "en"
    alert.article.short_summary = "Fast summary only."
    alert.article.matched_keywords = ["openai", "chip"]
    alert.article.selection_reason = "keyword 1.00; recency 1.00; official/source boost +0.10"

    text = format_alert_text(alert)

    assert "Mode: Fast Alert" in text
    assert "Original URL:" in text
    assert "Matched keywords/entities: openai, chip" in text
    assert "Source reliability/context:" in text
    assert "Why it matters:" not in text
    assert "Bullish scenario:" not in text
    assert "Risk notes:" not in text


def test_source_library_defaults_and_feed_detection():
    library = default_source_library()
    enabled = [item for item in library if item.enabled]
    categories = {item.category for item in library}
    sample_feed = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Example Feed</title><language>en</language>
    <item><title>OpenAI announces chip partnership</title><link>https://example.com/a</link></item>
    </channel></rss>"""

    metadata = detect_feed_metadata("https://example.com/feed.xml", sample_feed)

    assert len(library) >= 30
    assert 0 < len(enabled) < len(library)
    assert set(SOURCE_LIBRARY_CATEGORIES).issuperset(categories)
    assert metadata["name"] == "Example Feed"
    assert metadata["entries"] == 1
    assert metadata["sample_titles"] == ["OpenAI announces chip partnership"]


def test_enabled_source_library_items_are_built_as_sources():
    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "public_rss": {"enabled": False},
                "official_rss": {"enabled": False},
                "library": [
                    {
                        "id": "example-feed",
                        "name": "Example Feed",
                        "url": "https://example.com/feed.xml",
                        "enabled": True,
                        "language": "en",
                        "category": "Custom",
                        "reliability_score": 0.7,
                    }
                ],
            }
        }
    )

    sources = build_sources(config)

    assert any(source.name == "Example Feed" for source in sources)


def test_quality_scoring_explains_boosts_and_blacklist():
    topic = TopicConfig(name="AI", enabled=True, prompt="monitor", keywords=["OpenAI"])
    quality = QualitySettings(
        whitelist_sources=["official.example"],
        blacklist_sources=["blocked.example"],
        category_priority={"Official/Government": 0.05},
    )
    official = Article(
        "OpenAI announces chip partnership",
        "https://official.example/a",
        "Official Example",
        published_at=utc_now(),
        reliability_score=0.95,
        category="Official/Government",
    )
    blocked = Article(
        "OpenAI announces chip partnership",
        "https://blocked.example/a",
        "Blocked Example",
        published_at=utc_now(),
        reliability_score=0.95,
    )
    weaker = Article(
        "OpenAI announces chip partnership",
        "https://news.example/a",
        "Newswire",
        published_at=utc_now(),
        reliability_score=0.55,
    )

    ranked = rank_articles([weaker, blocked, official], topic, quality)

    assert blocked not in ranked
    assert ranked[0] is official
    assert "official/source boost" in official.selection_reason
    assert "whitelist boost" in official.selection_reason
    assert official.match_reason == "Matched keywords: openai"


def test_notification_fallback_routes_after_primary_failure(tmp_path: Path):
    class FakeNotifier:
        def __init__(self, name: str, success: bool):
            self.name = name
            self.success = success
            self.sent = 0

        def send(self, alert):
            self.sent += 1
            return NotificationResult(self.name, self.success, None if self.success else "failed")

    config = AppConfig(
        notifications=NotificationRoutingSettings(
            fallback_enabled=True,
            fallback_order=["email", "telegram"],
            retry_attempts=1,
            retry_base_delay_seconds=0,
        )
    )
    email = FakeNotifier("Email", False)
    telegram = FakeNotifier("Telegram", True)
    monitor = NewsMonitor(
        tmp_path / "config.yaml",
        tmp_path,
        store=SQLiteStore(tmp_path / "data" / "monitor.sqlite"),
        source_factory=lambda config: [],
        llm_factory=lambda config: None,
        notifier_factory=lambda settings, timeout: [],
    )

    monitor._send_notifications(sample_alert(), [email, telegram], config)

    assert email.sent == 1
    assert telegram.sent == 1
    assert monitor.status.notifier_health["Email"].startswith("error")
    assert monitor.status.notifier_health["Telegram"] == "ok"
