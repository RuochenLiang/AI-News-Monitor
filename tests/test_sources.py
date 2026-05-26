from __future__ import annotations

import httpx
import pytest

from src.config import parse_config
from src.models import TopicConfig
from src.monitor import build_sources
from src.sources.custom_rss import CustomRssSource
from src.sources.gdelt import GdeltSource, build_gdelt_query, sanitize_gdelt_keyword, validate_gdelt_query
from src.sources.library import SOURCE_PACKAGE_PRESETS, default_source_library
from src.sources.official_rss import OfficialRssSource

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Chip deal announced</title><link>https://example.com/chip</link><description>Semiconductor news</description><pubDate>Wed, 01 May 2024 10:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_official_rss_source_parses_mocked_feed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=RSS)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = OfficialRssSource(["https://example.com/rss"], client=client)
    topic = TopicConfig("Topic", True, "Prompt", ["chip"])

    articles = source.fetch(topic)

    assert len(articles) == 1
    assert articles[0].title == "Chip deal announced"
    assert articles[0].published_at is not None


def test_gdelt_source_parses_mocked_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "title": "AI chip news",
                        "url": "https://example.com/ai-chip",
                        "seendate": "20240501100000",
                        "language": "English",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = GdeltSource(client=client)
    topic = TopicConfig("Topic", True, "Prompt", ["AI chip"])

    articles = source.fetch(topic)

    assert len(articles) == 1
    assert articles[0].source == "GDELT"
    assert articles[0].published_at is not None


def test_gdelt_or_query_wraps_terms_in_parentheses():
    topic = TopicConfig("Topic", True, "Prompt", ["OpenAI", "NVIDIA", "Taiwan chips"])

    query = build_gdelt_query(topic)

    assert query == '("OpenAI" OR "NVIDIA" OR "Taiwan chips")'


def test_gdelt_keyword_sanitizer_removes_fragments_and_preserves_technical_terms():
    topic = TopicConfig("Semiconductor policy", True, "Prompt", ["HBM,", "DRAM,", "DDR5,", '"', ",", "AI,"])

    query = build_gdelt_query(topic)

    assert sanitize_gdelt_keyword("HBM,") == "HBM"
    assert sanitize_gdelt_keyword('"') is None
    assert query == '("HBM" OR "DRAM" OR "DDR5" OR "artificial intelligence")'
    assert len(query) <= GdeltSource.max_query_length


def test_gdelt_query_falls_back_to_topic_name_and_rejects_too_short_phrase():
    topic = TopicConfig("Taiwan semiconductor policy", True, "Prompt", ['"', ",", " "])

    assert build_gdelt_query(topic) == '"Taiwan semiconductor policy"'
    with pytest.raises(ValueError, match="too short"):
        validate_gdelt_query('"AI"')


def test_default_source_packages_have_rss_coverage_without_yahoo_default_activation():
    library = default_source_library()
    required = {
        "global-news-starter",
        "finance-starter",
        "official-gov-starter",
        "china-taiwan-starter",
        "us-policy-starter",
        "semiconductor-ai-starter",
        "company-ir-starter",
        "taiwan-semiconductor-official",
        "geopolitics-starter",
        "ai-industry-starter",
    }

    assert required <= set(SOURCE_PACKAGE_PRESETS)
    for package_id in required:
        assert [item for item in library if item.kind == "rss" and package_id in item.packages], package_id
    yahoo = next(item for item in library if item.id == "yahoo-finance")
    assert yahoo.kind == "website"
    assert parse_config({}).sources.yahoo_finance_rss.enabled is False


def test_build_sources_includes_custom_rss_source():
    from src.config import parse_config

    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "official_rss": {"enabled": False, "urls": []},
                "custom_sources": [{"name": "Custom Feed", "url": "https://example.com/rss.xml"}],
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )

    sources = build_sources(config)

    assert len(sources) == 1
    assert isinstance(sources[0], CustomRssSource)
    assert sources[0].name == "Custom Feed"
