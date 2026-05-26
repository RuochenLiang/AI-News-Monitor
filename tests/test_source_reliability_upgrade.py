from __future__ import annotations

from datetime import timedelta

import httpx

from src.config import parse_config
from src.models import Article, NotificationResult, RuntimeStatus, TopicConfig
from src.monitor import NewsMonitor
from src.realtime import LocalEventServer, SseBroker
from src.scoring import rank_articles
from src.source_reliability import (
    compute_coverage_quality,
    compute_freshness_state,
    compute_intelligence_gaps,
    next_backoff_seconds,
    source_package_status,
)
from src.sources.library import SOURCE_PACKAGE_PRESETS, apply_source_package_presets
from src.storage import SQLiteStore
from src.utils.time_utils import utc_now
from tests.helpers import start_server_or_skip
from tests.test_config import CONFIG_TEXT
from tests.test_llm_schema import VALID_JSON


class FakeLlm:
    api_key = "test"

    def __init__(self):
        self.calls = 0

    def analyze_article(self, topic, article):
        self.calls += 1
        from src.llm_client import parse_llm_analysis

        return parse_llm_analysis(VALID_JSON)


class FakeNotifier:
    name = "Fake Notifier"

    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)
        return NotificationResult(self.name, True)


def test_source_tier_role_parsing_and_custom_defaults():
    config = parse_config(
        {
            "sources": {
                "library": [
                    {
                        "id": "official-feed",
                        "name": "Official Feed",
                        "url": "https://example.com/rss.xml",
                        "category": "Official/Government",
                        "source_tier": 1,
                        "source_role": "official",
                        "propaganda_risk": "low",
                    }
                ],
                "custom_sources": [{"name": "Custom Feed", "url": "https://example.com/custom.xml"}],
            }
        }
    )

    official = next(item for item in config.sources.library if item.id == "official-feed")
    custom = config.sources.custom_sources[0]

    assert official.source_tier == 1
    assert official.source_role == "official"
    assert custom.source_tier == 4
    assert custom.source_role == "custom"
    assert custom.propaganda_risk == "unknown"


def test_freshness_state_computation():
    now = utc_now()
    settings = parse_config({}).source_health

    assert compute_freshness_state({"last_success_time": now, "articles": 1}, settings, now=now) == "fresh"
    assert (
        compute_freshness_state(
            {"last_success_time": now - timedelta(hours=3), "articles": 1},
            settings,
            now=now,
        )
        == "stale"
    )
    assert (
        compute_freshness_state(
            {"last_success_time": now - timedelta(hours=7), "articles": 1},
            settings,
            now=now,
        )
        == "very_stale"
    )
    assert compute_freshness_state({"last_fetch_time": now, "articles": 0}, settings, now=now) == "no_data"
    assert compute_freshness_state({"health": "error", "last_error_category": "feed_unreachable"}, settings) == "error"
    assert compute_freshness_state({}, settings, enabled=False) == "disabled"


def test_intelligence_gaps_and_coverage_quality_serialization():
    config = parse_config({"sources": {"enabled_packages": ["official-gov-starter"]}})
    now = utc_now()
    states = {
        item.name: {
            "enabled": True,
            "health": "ok",
            "last_fetch_time": now,
            "last_success_time": now,
            "articles": 2,
            "freshness_state": "fresh",
        }
        for item in config.sources.library
        if "official-gov-starter" in item.packages and item.kind == "rss"
    }

    gaps = compute_intelligence_gaps(config, states)
    coverage = compute_coverage_quality(config, states)

    assert gaps["summary"]["healthy"] > 0
    assert "critical_gaps" in gaps
    assert coverage["global"]["coverage_quality"] in {"high", "medium", "low", "critical"}
    assert coverage["global"]["reason"]


def test_intelligence_gap_severities_for_degraded_critical_language_and_topic_groups():
    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "public_rss": {"enabled": False},
                "official_rss": {"enabled": False},
                "custom_sources": [
                    {
                        "name": "Fresh Finance",
                        "url": "https://example.com/fresh.xml",
                        "category": "Finance",
                        "source_tier": 2,
                        "source_role": "major_media",
                    },
                    {
                        "name": "Stale Finance",
                        "url": "https://example.com/stale.xml",
                        "category": "Finance",
                        "source_tier": 2,
                        "source_role": "major_media",
                    },
                    {
                        "name": "Chinese Empty",
                        "url": "https://example.com/zh.xml",
                        "category": "China",
                        "default_language": "zh-CN",
                    },
                ],
            },
            "topics": [
                {
                    "name": "Taiwan chips",
                    "enabled": True,
                    "prompt": "Monitor Taiwan semiconductor policy.",
                    "keywords": ["Taiwan", "chip"],
                }
            ],
        }
    )
    now = utc_now()
    states = {
        "Fresh Finance": {"enabled": True, "health": "ok", "last_success_time": now, "articles": 2},
        "Stale Finance": {
            "enabled": True,
            "health": "ok",
            "last_success_time": now - timedelta(hours=3),
            "articles": 1,
        },
        "Chinese Empty": {"enabled": True, "health": "ok", "last_fetch_time": now, "articles": 0},
    }

    gaps = compute_intelligence_gaps(config, states)
    groups = {group["id"]: group for group in gaps["groups"]}

    assert groups["category:Finance"]["severity"] == "degraded"
    assert groups["focus:Official/Government"]["severity"] == "critical"
    assert groups["language:zh-CN"]["severity"] == "critical"
    assert groups["topic:Taiwan chips"]["severity"] == "critical"


def _coverage_config(source_tier: int = 1, include_stale: bool = False):
    sources = [
        ("Official Fresh", "Official/Government", "en", "official"),
        ("Finance Fresh", "Finance", "en", "major_media"),
        ("China Fresh", "China", "zh-CN", "major_media"),
        ("Taiwan Fresh", "Taiwan", "en", "official"),
        ("Semi Fresh", "Semiconductor/AI", "en", "niche_media"),
        ("Company Fresh", "Company IR", "en", "company_ir"),
    ]
    if include_stale:
        sources.append(("Finance Stale", "Finance", "en", "major_media"))
    return parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "public_rss": {"enabled": False},
                "official_rss": {"enabled": False},
                "custom_sources": [
                    {
                        "name": name,
                        "url": f"https://example.com/{index}.xml",
                        "category": category,
                        "default_language": language,
                        "source_tier": source_tier,
                        "source_role": role,
                    }
                    for index, (name, category, language, role) in enumerate(sources)
                ],
            }
        }
    )


def test_coverage_quality_high_medium_low_and_critical():
    now = utc_now()
    high_config = _coverage_config(source_tier=1)
    high_states = {
        source.name: {"enabled": True, "health": "ok", "last_success_time": now, "articles": 2}
        for source in high_config.sources.custom_sources
    }
    medium_config = _coverage_config(source_tier=1, include_stale=True)
    medium_states = {
        source.name: {
            "enabled": True,
            "health": "ok",
            "last_success_time": now - timedelta(hours=3) if "Stale" in source.name else now,
            "articles": 1,
        }
        for source in medium_config.sources.custom_sources
    }
    low_config = _coverage_config(source_tier=4)
    low_states = {
        source.name: {"enabled": True, "health": "ok", "last_success_time": now, "articles": 1}
        for source in low_config.sources.custom_sources
    }

    assert compute_coverage_quality(high_config, high_states)["global"]["coverage_quality"] == "high"
    assert compute_coverage_quality(medium_config, medium_states)["global"]["coverage_quality"] == "medium"
    assert compute_coverage_quality(low_config, low_states)["global"]["coverage_quality"] == "low"
    assert compute_coverage_quality(parse_config({}), {})["global"]["coverage_quality"] == "critical"


def test_source_cache_hit_and_cached_articles_do_not_alert_by_default(tmp_path):
    class CountingSource:
        name = "Counting Source"

        def __init__(self):
            self.calls = 0

        def fetch(self, topic):
            self.calls += 1
            return [Article("chip cache news", "https://example.com/cache", self.name, snippet="chip")]

    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")
    source = CountingSource()
    llm = FakeLlm()
    notifier = FakeNotifier()
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=SQLiteStore(tmp_path / "data" / "monitor.sqlite"),
        source_factory=lambda config: [source],
        llm_factory=lambda config: llm,
        notifier_factory=lambda settings, timeout: [notifier],
    )

    monitor.run_cycle()
    status = monitor.run_cycle()

    assert source.calls == 1
    assert llm.calls == 1
    assert len(notifier.sent) == 1
    assert status.source_states["Counting Source"]["cache_status"] == "cache_hit"


def test_source_state_persistence_roundtrip(tmp_path):
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    now = utc_now()
    state = {"health": "ok", "freshness_state": "fresh", "last_success_time": now, "articles": 3}

    store.save_source_state("Persisted Source", state)
    loaded = store.load_all_source_states()

    assert loaded["Persisted Source"]["freshness_state"] == "fresh"
    assert loaded["Persisted Source"]["articles"] == 3


def test_last_known_good_and_backoff_after_failure(tmp_path):
    class FlakySource:
        name = "Flaky Source"

        def __init__(self):
            self.calls = 0

        def fetch(self, topic):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("temporary failure")
            return [Article("chip fallback news", "https://example.com/fallback", self.name, snippet="chip")]

    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT + "\nsource_cache:\n  source_ttl_seconds: 0\n", encoding="utf-8")
    source = FlakySource()
    llm = FakeLlm()
    notifier = FakeNotifier()
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=SQLiteStore(tmp_path / "data" / "monitor.sqlite"),
        source_factory=lambda config: [source],
        llm_factory=lambda config: llm,
        notifier_factory=lambda settings, timeout: [notifier],
    )

    monitor.run_cycle()
    failed = monitor.run_cycle()
    skipped = monitor.run_cycle()

    assert source.calls == 2
    assert failed.source_states["Flaky Source"]["cache_status"] == "last_known_good"
    assert failed.source_states["Flaky Source"]["current_backoff_seconds"] > 0
    assert skipped.source_states["Flaky Source"]["backoff_active"] is True
    assert len(notifier.sent) == 1


def test_failing_source_does_not_block_healthy_source(tmp_path):
    class BrokenSource:
        name = "Broken Source"

        def fetch(self, topic):
            raise RuntimeError("failed")

    class HealthySource:
        name = "Healthy Source"

        def fetch(self, topic):
            return [Article("chip healthy news", "https://example.com/healthy", self.name, snippet="chip")]

    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")
    llm = FakeLlm()
    notifier = FakeNotifier()
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=SQLiteStore(tmp_path / "data" / "monitor.sqlite"),
        source_factory=lambda config: [BrokenSource(), HealthySource()],
        llm_factory=lambda config: llm,
        notifier_factory=lambda settings, timeout: [notifier],
    )

    status = monitor.run_cycle()

    assert status.source_states["Broken Source"]["freshness_state"] == "error"
    assert status.source_states["Healthy Source"]["freshness_state"] == "fresh"
    assert llm.calls == 1
    assert len(notifier.sent) == 1


def test_backoff_increases_and_resets_after_success():
    first = next_backoff_seconds(0, 1, default_interval_seconds=120, multiplier=2.0, max_backoff_minutes=60)
    second = next_backoff_seconds(first, 2, default_interval_seconds=120, multiplier=2.0, max_backoff_minutes=60)

    assert second > first


def test_multi_source_confirmation_boost_and_same_owner_penalty():
    topic = TopicConfig("AI", True, "monitor", ["chip"])
    official = Article(
        "Chip export policy announced",
        "https://official.example/a",
        "Official",
        snippet="chip",
        published_at=utc_now(),
        source_tier=1,
        source_role="official",
        ownership="Agency",
    )
    media = Article(
        "Chip export policy announced",
        "https://media.example/a",
        "Media",
        snippet="chip",
        published_at=utc_now(),
        source_tier=2,
        source_role="major_media",
        ownership="Independent Media",
    )
    same_owner = Article(
        "Chip export policy announced",
        "https://same.example/a",
        "Same Owner",
        snippet="chip",
        published_at=utc_now(),
        source_tier=2,
        source_role="major_media",
        ownership="Independent Media",
    )

    ranked = rank_articles([same_owner, media, official], topic)

    assert ranked[0].confirmation_source_count == 3
    assert ranked[0].independent_source_count == 2
    assert "Confirmed by 3 sources" in ranked[0].confirmation_summary
    assert "same-owner confirmation penalty" in same_owner.selection_reason


def test_source_package_presets_parse_and_apply_without_overwriting_custom_settings():
    config = parse_config({"sources": {"enabled_packages": ["global-news-starter"]}})
    updated = apply_source_package_presets(config.sources, ["ai-industry-starter"])
    package_rows = source_package_status(parse_config({"sources": {"enabled_packages": updated.enabled_packages}}), {})

    assert "ai-industry-starter" in updated.enabled_packages
    assert "global-news-starter" in updated.enabled_packages
    assert "ai-industry-starter" in SOURCE_PACKAGE_PRESETS
    assert any(row["id"] == "ai-industry-starter" and row["source_count"] > 0 for row in package_rows)


def test_local_reliability_endpoints_serialize_status():
    status = RuntimeStatus(
        state="Running",
        source_summary={"enabled_sources": 1, "fresh": 1},
        intelligence_gaps={"summary": {"healthy": 1, "degraded": 0, "critical": 0}, "critical_gaps": []},
        coverage_quality={"global": {"coverage_quality": "high", "reason": "ok"}},
        source_states={"Source": {"freshness_state": "fresh"}},
    )
    server = LocalEventServer("127.0.0.1", 0, SseBroker(), status_provider=lambda: status)
    start_server_or_skip(server)
    try:
        health = httpx.get(f"{server.url}/api/source-health").json()
        gaps = httpx.get(f"{server.url}/api/intelligence-gaps").json()
        coverage = httpx.get(f"{server.url}/api/coverage-quality").json()
    finally:
        server.stop()

    assert health["source_summary"]["fresh"] == 1
    assert gaps["summary"]["healthy"] == 1
    assert coverage["global"]["coverage_quality"] == "high"
