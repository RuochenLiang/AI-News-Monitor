from __future__ import annotations

from src.config import parse_config
from src.models import CustomNewsSourceConfig, TopicConfig
from src.monitor import _sources_for_topic
from src.sources.custom_rss import CustomRssSource
from src.sources.source_discovery import classify_topic_domains, discover_sources_for_topic
from src.sources.source_preview import topic_source_preview_lines


def test_auto_source_mode_selects_reasonable_tech_sources():
    config = parse_config({})
    topic = TopicConfig(
        name="AI infrastructure",
        enabled=True,
        prompt="Track AI chips, data centers, models, and cloud infrastructure.",
        keywords=["AI chips", "NVIDIA"],
        source_mode="auto",
        domains=["technology", "ai_industry", "semiconductor"],
    )

    selected = discover_sources_for_topic(topic, config.sources)
    names = {item.candidate.name for item in selected}

    assert "arXiv cs.AI" in names
    assert any("NVIDIA" in name or "AI" in name for name in names)
    assert all("domain match" in item.reason or item.candidate.domain_tags for item in selected)


def test_auto_source_mode_selects_reasonable_politics_sources():
    config = parse_config({})
    topic = TopicConfig(
        name="US China export controls",
        enabled=True,
        prompt="Track US-China technology policy and export control actions.",
        keywords=["export controls", "China"],
        source_mode="auto",
        domains=["politics", "geopolitics", "public_policy"],
    )

    selected = discover_sources_for_topic(topic, config.sources)
    names = {item.candidate.name for item in selected}

    assert "White House Briefing Room" in names or "U.S. Commerce News" in names
    assert any(item.candidate.country_or_region in {"US", "China", "Taiwan"} for item in selected)


def test_history_topic_does_not_use_breaking_news_only_sources():
    config = parse_config({})
    topic = TopicConfig(
        name="History of export controls",
        enabled=True,
        prompt="Build historical context on export control policy.",
        keywords=["export controls"],
        source_mode="auto",
        domains=["history"],
    )

    selected = discover_sources_for_topic(topic, config.sources)

    assert selected
    assert all("general_breaking_news" not in item.candidate.domain_tags for item in selected)


def test_domain_classification_uses_topic_text_when_domains_missing():
    topic = TopicConfig(
        name="Taiwan semiconductor policy",
        enabled=True,
        prompt="Monitor policy, trade, and export control developments.",
        keywords=["Taiwan", "chips"],
    )

    domains = classify_topic_domains(topic)

    assert "geopolitics" in domains
    assert "technology" in domains or "semiconductor" in domains


def test_manual_source_mode_serializes_selection_reason():
    config = parse_config({})
    topic = TopicConfig("Manual topic", True, "Prompt", ["chip"], source_mode="manual")
    source = CustomRssSource(CustomNewsSourceConfig("Manual Feed", "https://example.com/feed.xml"))

    selected_sources, summary = _sources_for_topic([source], topic, config)

    assert selected_sources == [source]
    assert summary == [
        {
            "topic": "Manual topic",
            "source_mode": "manual",
            "source": "Manual Feed",
            "source_type": "rss",
            "reason": "manual configured source",
            "expected_value": "user-selected source coverage",
            "risk": None,
            "priority": None,
            "auto_selected": False,
        }
    ]


def test_auto_source_mode_serializes_discovered_selection_reasons():
    config = parse_config({})
    topic = TopicConfig(
        name="AI infrastructure",
        enabled=True,
        prompt="Track AI chips and data centers.",
        keywords=["AI chips"],
        source_mode="auto",
        domains=["technology", "ai_industry", "semiconductor"],
    )

    selected_sources, summary = _sources_for_topic([], topic, config)

    assert selected_sources
    assert summary
    assert all(item["auto_selected"] is True for item in summary)
    assert any("domain match" in str(item["reason"]) for item in summary)
    assert all(item["expected_value"] for item in summary)


def test_topic_source_preview_shows_manual_and_auto_selection_reasons():
    config = parse_config(
        {
            "sources": {
                "custom_sources": [{"name": "Manual Feed", "url": "https://example.com/feed.xml"}],
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "official_rss": {"enabled": False},
                "public_rss": {"enabled": False},
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )
    topic = TopicConfig(
        name="AI infrastructure",
        enabled=True,
        prompt="Track AI chips and cloud infrastructure.",
        keywords=["AI chips", "NVIDIA"],
        source_mode="hybrid",
        domains=["technology", "ai_industry", "semiconductor"],
    )

    lines = topic_source_preview_lines(topic, config, "en")

    assert any("Manual sources" in line for line in lines)
    assert any("Manual Feed" in line for line in lines)
    assert any("Auto-selected candidates" in line for line in lines)
    assert any("reason:" in line and "expected:" in line for line in lines)
