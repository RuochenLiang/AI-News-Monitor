from __future__ import annotations

import httpx

from src.bias import annotate_bias_context, cluster_articles
from src.config import load_config, parse_config
from src.language import detect_supported_language, normalize_language
from src.models import Article, RuntimeStatus, TopicConfig
from src.notifiers.relay_webhook_notifier import RelayWebhookNotifier
from src.realtime import LocalEventServer, SseBroker
from src.scoring import rank_articles
from src.translation import enrich_article_language
from src.utils.time_utils import utc_now
from tests.helpers import start_server_or_skip


def test_language_detection_supports_chinese_and_english_only():
    assert normalize_language("Chinese") == "zh-CN"
    assert normalize_language("en-US") == "en"
    chinese_text = "".join(chr(codepoint) for codepoint in [0x7279, 0x6717, 0x666E, 0x53F0, 0x6E7E])
    assert detect_supported_language(chinese_text) == "zh-CN"
    assert detect_supported_language("OpenAI announces a new model") == "en"
    assert detect_supported_language("12345") is None


def test_ranking_prefers_recent_reliable_keyword_match():
    topic = TopicConfig(name="AI", enabled=True, prompt="monitor", keywords=["OpenAI"])
    recent = Article(
        "OpenAI launches chip partnership",
        "https://example.com/recent",
        "Official RSS",
        published_at=utc_now(),
        reliability_score=0.95,
    )
    weak = Article(
        "Generic technology roundup",
        "https://example.com/old",
        "Unknown",
        reliability_score=0.2,
    )

    ranked = rank_articles([weak, recent], topic)

    assert ranked[0] is recent
    assert recent.ranking_score > weak.ranking_score


def test_bias_context_clusters_same_event():
    articles = [
        Article("OpenAI announces Taiwan chip partnership", "https://a.example", "Source A"),
        Article("OpenAI announces Taiwan chip partnership", "https://b.example", "Source B", bias_hint="business"),
    ]

    clusters = cluster_articles(articles, min_cluster_size=2)
    annotate_bias_context(articles, True, "cluster", 2)

    assert len(clusters) == 1
    assert articles[0].event_cluster_id
    assert "Cross-source cluster" in articles[0].raw["bias_summary"]


def test_translation_enrichment_uses_llm_when_target_differs():
    class FakeClient:
        api_key = "test"

        def translate_and_summarize(self, article, target_language):
            translated_title = "".join(
                chr(codepoint) for codepoint in [0x004F, 0x0070, 0x0065, 0x006E, 0x0041, 0x0049, 0x53D1, 0x5E03]
            )
            summary = "".join(chr(codepoint) for codepoint in [0x7B80, 0x77ED, 0x6458, 0x8981])
            return {
                "translated_title": translated_title,
                "translated_snippet": summary,
                "summary": summary,
            }

    article = Article("OpenAI announces partnership", "https://example.com", "Source", language="en")

    enrich_article_language(
        article,
        target_language="zh-CN",
        translation_enabled=True,
        summary_enabled=True,
        llm_client=FakeClient(),
    )

    assert article.translated_title != article.title
    assert article.short_summary


def test_config_parses_next_phase_settings():
    config = parse_config(
        {
            "app": {"output_language": "en"},
            "enrichment": {"translation_enabled": True},
            "bias": {"enabled": True, "mode": "cluster", "min_cluster_size": 2},
            "local_server": {"enabled": True, "port": 8765},
            "sources": {"public_rss": {"enabled": True, "urls": ["https://example.com/feed.xml"]}},
            "notifiers": {
                "wechat": {"enabled": True, "provider": "serverchan"},
                "qq": {"enabled": True, "provider": "qmsg"},
            },
        }
    )

    assert config.enrichment.target_language == "en"
    assert config.bias.mode == "cluster"
    assert config.sources.public_rss.enabled is True
    assert config.notifiers.wechat.enabled is True


def test_relay_payload_shapes():
    notifier = RelayWebhookNotifier(
        parse_config({"notifiers": {"wechat": {"provider": "serverchan"}}}).notifiers.wechat
    )
    assert notifier._provider_payload("Title", "Body") == {"title": "Title", "desp": "Body"}


def test_local_event_server_health_and_status():
    broker = SseBroker()
    status = RuntimeStatus(state="Running", active_topics_count=2)
    server = LocalEventServer("127.0.0.1", 0, broker, status_provider=lambda: status)
    start_server_or_skip(server)
    try:
        health = httpx.get(f"{server.url}/health").json()
        payload = httpx.get(f"{server.url}/status").json()
    finally:
        server.stop()

    assert health["ok"] is True
    assert payload["state"] == "Running"
    assert payload["active_topics_count"] == 2


def test_local_event_server_control_endpoint():
    broker = SseBroker()
    calls: list[str] = []
    server = LocalEventServer(
        "127.0.0.1",
        0,
        broker,
        status_provider=lambda: RuntimeStatus(),
        control_handlers={"pause": lambda: calls.append("pause")},
    )
    start_server_or_skip(server)
    try:
        response = httpx.post(f"{server.url}/api/control", json={"action": "pause"})
    finally:
        server.stop()

    assert response.json() == {"ok": True, "action": "pause"}
    assert calls == ["pause"]


def test_local_event_server_setup_endpoint_is_read_only(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  output_language: en
notifiers:
  email:
    enabled: false
topics: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("", encoding="utf-8")
    for key in ["LLM_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        monkeypatch.delenv(key, raising=False)

    broker = SseBroker()
    server = LocalEventServer(
        "127.0.0.1",
        0,
        broker,
        status_provider=lambda: RuntimeStatus(),
        config_path=config_path,
        runtime_dir=tmp_path,
    )
    start_server_or_skip(server)
    try:
        initial = httpx.get(f"{server.url}/api/setup").json()
        response = httpx.post(
            f"{server.url}/api/setup",
            json={
                "llm": {"model": "test-model", "api_key": "sk-test-value"},
                "sources": {"enabled_packages": ["global-news-starter"]},
            },
        )
    finally:
        server.stop()

    config = load_config(config_path)
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert initial["setup_required"] is True
    assert initial["helper_links"]["openai_keys"].startswith("https://")
    assert response.status_code == 405
    assert "read-only" in response.text
    assert "sk-test-value" not in response.text
    assert config.llm.model != "test-model"
    assert config.sources.enabled_packages == []
    assert config.topics == []
    assert "LLM_API_KEY=sk-test-value" not in env_text


def test_local_event_server_setup_endpoint_rejects_source_library_toggle(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  output_language: en
sources:
  gdelt:
    enabled: false
  google_news_rss:
    enabled: false
  yahoo_finance_rss:
    enabled: false
  public_rss:
    enabled: false
  official_rss:
    enabled: false
notifiers:
  email:
    enabled: false
topics: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("", encoding="utf-8")
    server = LocalEventServer(
        "127.0.0.1",
        0,
        SseBroker(),
        status_provider=lambda: RuntimeStatus(),
        config_path=config_path,
        runtime_dir=tmp_path,
    )
    start_server_or_skip(server)
    try:
        response = httpx.post(
            f"{server.url}/api/setup",
            json={"sources": {"library_enabled": {"bbc-world": True}}},
        )
    finally:
        server.stop()

    config = load_config(config_path)
    enabled = {item.id for item in config.sources.library if item.enabled}

    assert response.status_code == 405
    assert "read-only" in response.text
    assert "bbc-world" not in enabled


def test_local_event_server_setup_endpoint_rejects_custom_source_changes(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  output_language: en
sources:
  gdelt:
    enabled: false
  google_news_rss:
    enabled: false
  yahoo_finance_rss:
    enabled: false
  public_rss:
    enabled: false
  official_rss:
    enabled: false
notifiers:
  email:
    enabled: false
topics: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("", encoding="utf-8")
    server = LocalEventServer(
        "127.0.0.1",
        0,
        SseBroker(),
        status_provider=lambda: RuntimeStatus(),
        config_path=config_path,
        runtime_dir=tmp_path,
    )
    start_server_or_skip(server)
    try:
        added = httpx.post(
            f"{server.url}/api/setup",
            json={
                "sources": {
                    "custom_source": {
                        "name": "Custom AI Feed",
                        "url": "https://example.com/feed.xml",
                        "category": "Custom",
                        "default_language": "en",
                        "reliability_score": 0.7,
                    }
                }
            },
        )
    finally:
        server.stop()

    config = load_config(config_path)

    assert added.status_code == 405
    assert "read-only" in added.text
    assert config.sources.custom_sources == []


def test_local_event_server_test_endpoint_is_read_only(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  output_language: en
notifiers:
  telegram:
    enabled: true
topics: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("", encoding="utf-8")
    for key in ["LLM_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        monkeypatch.delenv(key, raising=False)

    broker = SseBroker()
    server = LocalEventServer(
        "127.0.0.1",
        0,
        broker,
        status_provider=lambda: RuntimeStatus(),
        config_path=config_path,
        runtime_dir=tmp_path,
    )
    start_server_or_skip(server)
    try:
        llm = httpx.post(f"{server.url}/api/test", json={"target": "llm"})
        telegram = httpx.post(f"{server.url}/api/test", json={"target": "telegram"})
        setup = httpx.get(f"{server.url}/api/setup").json()
    finally:
        server.stop()

    assert llm.status_code == 405
    assert telegram.status_code == 405
    assert "read-only" in llm.text
    assert "read-only" in telegram.text
    assert setup["llm"]["last_test_result"] is None
    assert setup["notifications"]["channels"]["telegram"]["last_test_result"] is None
