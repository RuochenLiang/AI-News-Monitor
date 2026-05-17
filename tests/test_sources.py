from __future__ import annotations

import httpx

from src.models import TopicConfig
from src.monitor import build_sources
from src.sources.custom_rss import CustomRssSource
from src.sources.gdelt import GdeltSource
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
