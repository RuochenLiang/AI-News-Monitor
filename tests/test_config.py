from __future__ import annotations

import pytest

from src.config import ConfigError, config_to_dict, load_config, parse_config, validate_config, validate_topic
from src.models import TopicConfig
from src.secrets import get_env_secret, mask_secret, sanitize_for_log

CONFIG_TEXT = """
app:
  output_language: zh-CN
monitor:
  default_interval_seconds: 120
  min_relevance_score: 80
  max_alerts_per_hour: 5
  deduplicate_hours: 72
  request_timeout_seconds: 20
llm:
  provider: openai_compatible
  base_url: https://api.openai.com/v1
  model: test-model
  api_key_env: LLM_API_KEY
topics:
  - name: Test Topic
    enabled: true
    prompt: Watch this topic.
    keywords: ["chip"]
notifiers:
  email:
    enabled: false
"""


def test_config_loading_and_env_secret(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / ".env"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")
    env_path.write_text("LLM_API_KEY=local-secret\n", encoding="utf-8")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    config = load_config(config_path)

    assert config.llm.model == "test-model"
    assert config.topics[0].name == "Test Topic"
    assert get_env_secret("LLM_API_KEY") == "local-secret"


def test_topic_validation_requires_keyword_unless_broad_search():
    topic = TopicConfig(name="A", enabled=True, prompt="Prompt", keywords=[])
    with pytest.raises(ConfigError):
        validate_topic(topic)
    topic.broad_search = True
    validate_topic(topic)


def test_topic_validation_rejects_bad_url():
    topic = TopicConfig(
        name="A",
        enabled=True,
        prompt="Prompt",
        keywords=["x"],
        official_rss_urls=["not-a-url"],
    )
    with pytest.raises(ConfigError):
        validate_topic(topic)


def test_secret_masking_and_log_sanitization(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-secret-value")
    assert mask_secret("abcdefghi").startswith("ab")
    sanitized = sanitize_for_log("api_key=sk-secret-value token=abc123")
    assert "sk-secret-value" not in sanitized
    assert "abc123" not in sanitized


def test_recommended_presets_apply_and_prune_optional_values():
    config = parse_config(
        {
            "llm": {
                "preset": "recommended",
                "provider": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key_env": "LLM_API_KEY",
            },
            "notifiers": {"email": {"preset": "recommended", "enabled": True, "to_addrs": ["a@example.com"]}},
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )

    assert config.llm.temperature == 0.7
    assert config.llm.top_p == 1.0
    assert config.llm.presence_penalty == 0.0
    assert config.llm.max_tokens == 1024
    saved = config_to_dict(config)
    assert "temperature" not in saved["llm"]
    assert "smtp_host" not in saved["notifiers"]["email"]


def test_custom_news_source_validation_rejects_duplicates():
    config = parse_config(
        {
            "sources": {
                "custom_sources": [
                    {"name": "Feed", "url": "https://example.com/feed.xml"},
                    {"name": "Feed", "url": "https://example.com/other.xml"},
                ]
            },
            "topics": [{"name": "T", "enabled": True, "prompt": "P", "keywords": ["k"]}],
        }
    )
    with pytest.raises(ConfigError):
        validate_config(config)
