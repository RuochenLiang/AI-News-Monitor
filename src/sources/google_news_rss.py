from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

from src.models import Article, TopicConfig
from src.sources.base import NewsSource
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)


class GoogleNewsRssSource(NewsSource):
    name = "Google News RSS"

    def __init__(self, timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.timeout_seconds = timeout_seconds
        self.client = client

    def fetch(self, topic: TopicConfig) -> list[Article]:
        queries = topic.keywords or [topic.name]
        articles: list[Article] = []
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            for query in queries[:8]:
                url = (
                    "https://news.google.com/rss/search?"
                    f"q={quote_plus(query)}&hl={topic.output_language}&gl=US&ceid=US:en"
                )
                response = request_with_retries(client, "GET", url)
                articles.extend(
                    parse_feed(
                        response.content,
                        self.name,
                        topic.output_language,
                        reliability_score=0.65,
                        ownership="Google News aggregated publisher feed",
                        bias_hint="aggregator; ranking can reflect source availability and region",
                        category="Global News",
                        source_type="aggregator",
                        source_tier=4,
                        source_role="aggregator",
                        propaganda_risk="unknown",
                        editorial_context="Aggregator feed; verify original publisher context.",
                    )
                )
        finally:
            if close_client:
                client.close()
        logger.info("%s fetched %s articles for topic %s", self.name, len(articles), topic.name)
        return articles
