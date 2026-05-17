from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import Article, TopicConfig


class NewsSource(ABC):
    name: str

    @abstractmethod
    def fetch(self, topic: TopicConfig) -> list[Article]:
        raise NotImplementedError
