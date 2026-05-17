from __future__ import annotations

import logging

import httpx

from src.models import Article, CustomNewsSourceConfig, TopicConfig
from src.sources.base import NewsSource
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)


class CustomRssSource(NewsSource):
    def __init__(
        self,
        source_config: CustomNewsSourceConfig,
        timeout_seconds: int = 20,
        client: httpx.Client | None = None,
    ):
        self.source_config = source_config
        self.name = source_config.name
        self.timeout_seconds = timeout_seconds
        self.client = client

    def fetch(self, topic: TopicConfig) -> list[Article]:
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            response = request_with_retries(client, "GET", self.source_config.url)
            articles = parse_feed(
                response.content,
                self.name,
                self.source_config.default_language or topic.output_language,
                reliability_score=self.source_config.reliability_score,
                ownership=self.source_config.ownership,
                bias_hint=self.source_config.bias_hint,
                category=self.source_config.category,
                source_type=self.source_config.kind,
                source_url=self.source_config.url,
                source_tier=self.source_config.source_tier,
                source_role=self.source_config.source_role,
                state_affiliated=self.source_config.state_affiliated,
                propaganda_risk=self.source_config.propaganda_risk,
                editorial_context=self.source_config.editorial_context,
            )
        finally:
            if close_client:
                client.close()
        logger.info("%s fetched %s articles for topic %s", self.name, len(articles), topic.name)
        return articles
