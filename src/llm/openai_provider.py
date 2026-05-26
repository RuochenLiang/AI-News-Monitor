from __future__ import annotations

import httpx

from src.llm.provider_base import LLMProvider
from src.llm_client import LLMClient
from src.models import Article, EventCluster, LLMAnalysis, LLMSettings, TopicConfig


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, settings: LLMSettings, api_key: str | None = None, client: httpx.Client | None = None):
        self.client = LLMClient(settings, api_key=api_key, client=client)
        self.api_key = self.client.api_key

    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        return self.client.analyze_article(topic, article)

    def analyze_event_cluster(self, topic: TopicConfig, cluster: EventCluster) -> LLMAnalysis:
        return self.client.analyze_event_cluster(topic, cluster)

    def translate_and_summarize(self, article: Article, target_language: str) -> dict[str, str]:
        return self.client.translate_and_summarize(article, target_language)
