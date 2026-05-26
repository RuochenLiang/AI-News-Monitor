from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from src.llm.deepseek_provider import DeepSeekProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.provider_base import LLMProvider
from src.models import AppConfig, Article, EventCluster, LLMAnalysis, LLMProviderSettings, LLMSettings, TopicConfig


class LLMRouter:
    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers
        self.api_key = next((provider.api_key for provider in providers if provider.api_key), None)

    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        return self._call(lambda provider: provider.analyze_article(topic, article))

    def analyze_event_cluster(self, topic: TopicConfig, cluster: EventCluster) -> LLMAnalysis:
        return self._call(lambda provider: provider.analyze_event_cluster(topic, cluster))

    def translate_and_summarize(self, article: Article, target_language: str) -> dict[str, str]:
        return self._call(lambda provider: provider.translate_and_summarize(article, target_language))

    def _call(self, operation: Callable[[LLMProvider], object]):
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                return operation(provider)
            except Exception as exc:  # noqa: BLE001 - fallback routing must catch provider failures
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise RuntimeError("No enabled LLM providers are configured.")


def build_llm_client(config: AppConfig) -> LLMProvider:
    provider_names = [config.llm.provider, *config.llm.fallback_providers]
    providers = [
        _build_provider(name, config.llm)
        for name in dict.fromkeys(provider_names)
        if _provider_enabled(name, config.llm)
    ]
    if len(providers) == 1:
        return providers[0]
    return LLMRouter(providers)


def _provider_enabled(name: str, settings: LLMSettings) -> bool:
    provider = settings.providers.get(name)
    if provider is not None:
        return provider.enabled
    return True


def _build_provider(name: str, settings: LLMSettings) -> LLMProvider:
    provider_settings = settings.providers.get(name)
    client_settings = _settings_for_provider(name, settings, provider_settings)
    if name == "deepseek":
        return DeepSeekProvider(client_settings)
    return OpenAIProvider(client_settings)


def _settings_for_provider(
    name: str,
    settings: LLMSettings,
    provider: LLMProviderSettings | None,
) -> LLMSettings:
    if provider is None:
        return replace(settings, provider="openai_compatible")
    return replace(
        settings,
        provider="openai_compatible",
        base_url=provider.base_url,
        model=provider.model,
        api_key_env=provider.api_key_env,
        structured_outputs=provider.structured_outputs,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        retry_backoff_seconds=provider.retry_backoff_seconds,
    )
