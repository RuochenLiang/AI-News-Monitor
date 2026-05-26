from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import Article, EventCluster, LLMAnalysis, TopicConfig


class LLMProvider(ABC):
    name: str
    api_key: str | None

    @abstractmethod
    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        raise NotImplementedError

    @abstractmethod
    def analyze_event_cluster(self, topic: TopicConfig, cluster: EventCluster) -> LLMAnalysis:
        raise NotImplementedError

    @abstractmethod
    def translate_and_summarize(self, article: Article, target_language: str) -> dict[str, str]:
        raise NotImplementedError
