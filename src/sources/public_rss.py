from __future__ import annotations

import logging

import httpx

from src.models import Article, TopicConfig
from src.sources.base import NewsSource
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)


class PublicRssSource(NewsSource):
    name = "Global Public RSS"

    def __init__(self, urls: list[str], timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.urls = urls
        self.timeout_seconds = timeout_seconds
        self.client = client

    def fetch(self, topic: TopicConfig) -> list[Article]:
        articles: list[Article] = []
        if not self.urls:
            return articles
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            for url in self.urls:
                response = request_with_retries(client, "GET", url)
                articles.extend(
                    parse_feed(
                        response.content,
                        self.name,
                        "en",
                        reliability_score=0.72,
                        ownership="public technology and research RSS feeds",
                        bias_hint="publisher-specific framing; compare with primary source where possible",
                        category="Global News",
                        source_type="rss",
                        source_tier=3,
                        source_role="niche_media",
                        propaganda_risk="unknown",
                        editorial_context="User-configured public RSS group.",
                    )
                )
        finally:
            if close_client:
                client.close()
        logger.info("%s fetched %s articles for topic %s", self.name, len(articles), topic.name)
        return articles
