from __future__ import annotations

import pytest

from src.config import parse_config
from src.llm.router import LLMRouter, build_llm_client
from src.llm_client import LLMClient
from src.models import LLMAnalysis
from tests.test_llm_schema import VALID_JSON


class FailingProvider:
    name = "failing"
    api_key = "bad"

    def analyze_article(self, topic, article):
        raise RuntimeError("provider failed")

    def analyze_event_cluster(self, topic, cluster):
        raise RuntimeError("provider failed")

    def translate_and_summarize(self, article, target_language):
        raise RuntimeError("provider failed")


class WorkingProvider:
    name = "working"
    api_key = "ok"

    def analyze_article(self, topic, article):
        from src.llm_client import parse_llm_analysis

        return parse_llm_analysis(VALID_JSON)

    def analyze_event_cluster(self, topic, cluster):
        from src.llm_client import parse_llm_analysis

        return parse_llm_analysis(VALID_JSON)

    def translate_and_summarize(self, article, target_language):
        return {"translated_title": "t", "translated_snippet": "s", "summary": "m"}


def test_deepseek_config_resolves_provider_defaults_without_breaking_openai():
    config = parse_config(
        {
            "llm": {
                "provider": "deepseek",
                "fallback_providers": ["openai"],
                "providers": {
                    "openai": {"enabled": True, "api_key_env": "OPENAI_API_KEY", "model": "gpt-4.1-mini"},
                    "deepseek": {"enabled": True, "api_key_env": "DEEPSEEK_API_KEY"},
                },
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )

    assert config.llm.provider == "deepseek"
    assert config.llm.base_url == "https://api.deepseek.com"
    assert config.llm.model == "deepseek-v4-flash"
    assert config.llm.providers["openai"].model == "gpt-4.1-mini"


def test_build_llm_client_returns_router_for_fallback_providers():
    config = parse_config(
        {
            "llm": {
                "provider": "deepseek",
                "fallback_providers": ["openai"],
                "providers": {
                    "deepseek": {"enabled": True, "api_key_env": "DEEPSEEK_API_KEY"},
                    "openai": {"enabled": True, "api_key_env": "OPENAI_API_KEY"},
                },
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )

    client = build_llm_client(config)

    assert isinstance(client, LLMRouter)


def test_llm_router_falls_back_after_provider_failure():
    router = LLMRouter([FailingProvider(), WorkingProvider()])

    result = router.analyze_article(None, None)

    assert isinstance(result, LLMAnalysis)
    assert result.summary == "Summary"


def test_llm_router_raises_last_error_when_all_providers_fail():
    router = LLMRouter([FailingProvider()])

    with pytest.raises(RuntimeError, match="provider failed"):
        router.analyze_article(None, None)


def test_llm_client_uses_configured_retry_backoff(monkeypatch):
    config = parse_config(
        {
            "llm": {
                "provider": "openai",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key_env": "OPENAI_API_KEY",
                        "retry_backoff_seconds": 2.5,
                        "max_retries": 4,
                    }
                },
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )
    calls = {}

    def fake_request_with_retries(client, method, url, **kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr("src.llm_client.request_with_retries", fake_request_with_retries)
    client = LLMClient(config.llm, api_key="sk-test")

    client._send_chat_request(object(), {"messages": []}, retries=3)

    assert calls["retries"] == 3
    assert calls["backoff_seconds"] == 2.5
