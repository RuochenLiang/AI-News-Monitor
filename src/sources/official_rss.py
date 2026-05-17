from __future__ import annotations

import logging

import httpx

from src.models import Article, TopicConfig
from src.sources.base import NewsSource
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)


class OfficialRssSource(NewsSource):
    name = "Official RSS"

    def __init__(
        self, global_urls: list[str] | None = None, timeout_seconds: int = 20, client: httpx.Client | None = None
    ):
        self.global_urls = global_urls or []
        self.timeout_seconds = timeout_seconds
        self.client = client

    def fetch(self, topic: TopicConfig) -> list[Article]:
        urls = [*self.global_urls, *topic.official_rss_urls]
        articles: list[Article] = []
        if not urls:
            return articles
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            for url in urls:
                response = request_with_retries(client, "GET", url)
                articles.extend(
                    parse_feed(
                        response.content,
                        self.name,
                        topic.output_language,
                        reliability_score=0.9,
                        ownership="official publisher or organization feed",
                        bias_hint="primary source; may emphasize the publisher's own framing",
                        category="Official/Government",
                        source_type="rss",
                        source_tier=1,
                        source_role="official",
                        state_affiliated=True,
                        propaganda_risk="low",
                        editorial_context="Official or primary source feed.",
                    )
                )
        finally:
            if close_client:
                client.close()
        logger.info("%s fetched %s articles for topic %s", self.name, len(articles), topic.name)
        return articles
