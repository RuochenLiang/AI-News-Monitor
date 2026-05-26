from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.config import ConfigError, parse_config, validate_config
from src.models import SocialPostItem, TopicConfig, XCostGuardSettings, XSourceSettings
from src.monitor import _sources_for_topic, build_sources
from src.sources.social.x_client import XClient
from src.sources.social.x_query_builder import build_x_recent_search_queries
from src.sources.social.x_source import XRecentSearchSource


def test_x_source_is_disabled_by_default():
    config = parse_config({})

    assert config.social_sources.x.enabled is False
    assert config.social_sources.x.bearer_token_env == "X_BEARER_TOKEN"


def test_x_source_requires_bearer_token_env_name_when_enabled():
    config = parse_config({"social_sources": {"x": {"enabled": True, "bearer_token_env": ""}}})

    with pytest.raises(ConfigError, match="bearer_token_env"):
        validate_config(config)


def test_x_client_requires_bearer_token_when_enabled(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    client = XClient(XSourceSettings(enabled=True))

    with pytest.raises(ValueError, match="bearer token"):
        client.validate_ready()


def test_x_client_respects_zero_result_limit_without_network():
    client = XClient(XSourceSettings(enabled=True), bearer_token="token")
    topic = TopicConfig("AI chips", True, "Prompt", ["NVIDIA"], social_enabled=True)

    assert client.recent_search(topic, max_results=0) == []


def test_x_query_builder_uses_keywords_and_excludes_retweets_by_default():
    topic = TopicConfig("AI chips", True, "Prompt", ["NVIDIA", "HBM"], social_enabled=True)
    queries = build_x_recent_search_queries(topic, XSourceSettings())

    assert queries
    assert any("NVIDIA" in query for query in queries)
    assert all("-is:retweet" in query for query in queries)


def test_build_sources_adds_x_source_when_global_x_enabled():
    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "public_rss": {"enabled": False},
                "official_rss": {"enabled": False},
            },
            "social_sources": {"x": {"enabled": True}},
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )

    sources = build_sources(config)

    assert any(isinstance(source, XRecentSearchSource) for source in sources)


def test_x_recent_search_source_queries_only_for_enabled_auto_or_hybrid_topic():
    class FakeXClient:
        def __init__(self):
            self.calls = 0

        def recent_search(self, topic, max_results=None):
            self.calls += 1
            return [
                SocialPostItem(
                    platform="x",
                    post_id="1",
                    url="https://x.com/example/status/1",
                    author_id="42",
                    author_username="example",
                    text="NVIDIA posts an AI chip update.",
                    created_at=datetime(2026, 5, 26, tzinfo=UTC),
                    metrics={"author_followers_count": 5000},
                    referenced_urls=["https://example.com/source"],
                    source_confidence_hint=0.3,
                )
            ]

    client = FakeXClient()
    source = XRecentSearchSource(XSourceSettings(enabled=True, trusted_accounts=["example"]), client=client)
    manual = TopicConfig("AI chips", True, "Prompt", ["NVIDIA"], source_mode="manual", social_enabled=True)
    auto = TopicConfig("AI chips", True, "Prompt", ["NVIDIA"], source_mode="auto", social_enabled=True)

    assert source.fetch(manual) == []
    articles = source.fetch(auto)

    assert client.calls == 1
    assert len(articles) == 1
    assert articles[0].source_type == "x"
    assert articles[0].reliability_score == 0.3
    assert "unconfirmed" in articles[0].editorial_context


def test_auto_source_selection_includes_x_only_when_topic_allows_social():
    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "public_rss": {"enabled": False},
                "official_rss": {"enabled": False},
            },
            "social_sources": {"x": {"enabled": True}},
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )
    sources = build_sources(config)
    manual = TopicConfig("Manual", True, "Prompt", ["policy"], source_mode="manual", social_enabled=True)
    auto = TopicConfig("Auto", True, "Prompt", ["policy"], source_mode="auto", social_enabled=True)
    social_disabled = TopicConfig("No social", True, "Prompt", ["policy"], source_mode="auto", social_enabled=False)

    manual_sources, manual_summary = _sources_for_topic(sources, manual, config)
    auto_sources, auto_summary = _sources_for_topic(sources, auto, config)
    disabled_sources, disabled_summary = _sources_for_topic(sources, social_disabled, config)

    assert not any(isinstance(source, XRecentSearchSource) for source in manual_sources)
    assert not any(item["source_type"] == "x" for item in manual_summary)
    assert any(isinstance(source, XRecentSearchSource) for source in auto_sources)
    assert any(item["source_type"] == "x" for item in auto_summary)
    assert not any(isinstance(source, XRecentSearchSource) for source in disabled_sources)
    assert not any(item["source_type"] == "x" for item in disabled_summary)


def test_x_recent_search_source_stops_when_daily_cost_guard_is_exhausted():
    class FakeXClient:
        def __init__(self):
            self.calls = 0
            self.max_results_seen = []

        def recent_search(self, topic, max_results=None):
            self.calls += 1
            self.max_results_seen.append(max_results)
            return [
                SocialPostItem(
                    platform="x",
                    post_id=str(index),
                    url=f"https://x.com/example/status/{index}",
                    author_id="42",
                    author_username="example",
                    text=f"Policy signal {index}",
                    created_at=datetime(2026, 5, 26, tzinfo=UTC),
                    metrics={},
                    referenced_urls=[],
                    source_confidence_hint=0.3,
                )
                for index in range(max_results or 0)
            ]

    settings = XSourceSettings(
        enabled=True,
        max_posts_per_topic_per_run=25,
        cost_guard=XCostGuardSettings(enabled=True, daily_max_read_posts=10, warn_when_reaching_percent=80),
    )
    source = XRecentSearchSource(settings, client=FakeXClient())
    topic = TopicConfig("Policy", True, "Prompt", ["policy"], source_mode="auto", social_enabled=True)

    first = source.fetch(topic)
    first_warning = source.last_cost_guard_warning
    second = source.fetch(topic)

    assert len(first) == 10
    assert second == []
    assert source.client.calls == 1
    assert source.client.max_results_seen == [10]
    assert "100%" in (first_warning or "")
    assert "exhausted" in (source.last_cost_guard_warning or "")
