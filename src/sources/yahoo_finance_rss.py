from __future__ import annotations

import logging

import httpx

from src.models import Article, TopicConfig
from src.sources.base import NewsSource
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)


class YahooFinanceRssSource(NewsSource):
    name = "Yahoo Finance RSS"

    FEEDS = (
        "https://finance.yahoo.com/news/rssindex",
        "https://finance.yahoo.com/rss/topstories",
    )

    def __init__(self, timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.timeout_seconds = timeout_seconds
        self.client = client

    def fetch(self, topic: TopicConfig) -> list[Article]:
        articles: list[Article] = []
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            for url in self.FEEDS:
                response = request_with_retries(client, "GET", url)
                articles.extend(
                    parse_feed(
                        response.content,
                        self.name,
                        "en",
                        reliability_score=0.75,
                        ownership="Yahoo Finance aggregated finance feed",
                        bias_hint="finance-focused editorial and wire aggregation",
                        category="Finance",
                        source_type="aggregator",
                        source_tier=4,
                        source_role="aggregator",
                        propaganda_risk="unknown",
                        editorial_context="Finance aggregator feed; verify original publisher context.",
                    )
                )
        finally:
            if close_client:
                client.close()
        logger.info("%s fetched %s articles for topic %s", self.name, len(articles), topic.name)
        return articles
