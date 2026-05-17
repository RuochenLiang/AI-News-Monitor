from __future__ import annotations

import json
import smtplib

import httpx

from src.config import parse_config
from src.diagnostics import diagnostic_error, diagnostic_ok
from src.llm_client import LLMClient
from src.models import EmailSettings
from src.notifiers.email_notifier import EmailNotifier
from src.realtime import _index_html, _setup_snapshot, _test_enabled_sources
from src.sources.library import diagnose_feed_url

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>AI update</title><link>https://example.com/a</link></item>
</channel></rss>"""


def test_llm_diagnostic_reports_missing_api_key():
    client = LLMClient(parse_config({}).llm, api_key="")

    result = client.diagnose().to_dict()

    assert result["ok"] is False
    assert result["category"] == "missing_required_field"
    assert result["missing_fields"] == ["api_key"]
    assert "API key" in result["message"]


def test_llm_diagnostic_checks_models_and_chat_completion():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "test-model"}]})
        if request.url.path.endswith("/chat/completions"):
            seen["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})
        return httpx.Response(404)

    settings = parse_config({"llm": {"model": "test-model"}}).llm
    result = LLMClient(
        settings, api_key="sk-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    ).diagnose()

    assert result.ok is True
    assert result.details["chat_endpoint"] == "ok"
    assert result.details["available_models_sample"] == ["test-model"]
    assert "max_tokens" in seen["body"]


def test_llm_diagnostic_uses_max_completion_tokens_for_gpt_5_models():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "gpt-5.4-mini"}]})
        if request.url.path.endswith("/chat/completions"):
            seen["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})
        return httpx.Response(404)

    settings = parse_config({"llm": {"model": "gpt-5.4-mini"}}).llm
    result = LLMClient(
        settings, api_key="sk-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    ).diagnose()

    assert result.ok is True
    assert "max_completion_tokens" in seen["body"]
    assert "max_tokens" not in seen["body"]


def test_llm_diagnostic_classifies_rejected_key():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    result = LLMClient(
        parse_config({}).llm,
        api_key="sk-test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ).diagnose()

    assert result.ok is False
    assert result.category == "invalid_api_key"


def test_email_diagnostic_sends_with_fake_smtp(monkeypatch):
    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(f"connect:{host}:{port}:{timeout}")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            calls.append("starttls")

        def login(self, username, password):
            calls.append(f"login:{username}:{password}")

        def send_message(self, message):
            calls.append(f"send:{message['To']}")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setenv("EMAIL_FROM", "sender@example.com")

    result = EmailNotifier(EmailSettings(to_addrs=["receiver@example.com"])).send_test_diagnostic()

    assert result.ok is True
    assert calls == [
        "connect:smtp.gmail.com:587:20",
        "starttls",
        "login:sender@example.com:app-password",
        "send:receiver@example.com",
    ]


def test_email_diagnostic_classifies_smtp_auth_failure(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "wrong")
    monkeypatch.setenv("EMAIL_FROM", "sender@example.com")

    result = EmailNotifier(EmailSettings(to_addrs=["receiver@example.com"])).send_test_diagnostic()

    assert result.ok is False
    assert result.category == "smtp_auth_failed"
    assert result.suggested_fix


def test_source_diagnostic_classifies_valid_and_empty_feeds():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/empty":
            return httpx.Response(200, content=b"<rss><channel><title>Empty</title></channel></rss>")
        return httpx.Response(200, content=RSS)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    ok = diagnose_feed_url("https://example.com/rss", client=client)
    empty = diagnose_feed_url("https://example.com/empty", client=client)

    assert ok.ok is True
    assert ok.details["entries"] == 1
    assert empty.ok is False
    assert empty.category == "feed_empty"


def test_bulk_enabled_source_summary_uses_standard_diagnostics(monkeypatch):
    config = parse_config(
        {
            "sources": {
                "gdelt": {"enabled": False},
                "google_news_rss": {"enabled": False},
                "yahoo_finance_rss": {"enabled": False},
                "public_rss": {"enabled": True, "urls": ["https://ok.example/rss", "https://bad.example/rss"]},
                "official_rss": {"enabled": False},
            }
        }
    )

    def fake_diagnose(url, timeout_seconds, client=None):
        if "bad" in url:
            return diagnostic_error("source", "feed_unreachable", "Feed failed.")
        return diagnostic_ok("source", "Feed passed.", details={"entries": 1})

    monkeypatch.setattr("src.realtime.diagnose_feed_url", fake_diagnose)

    result = _test_enabled_sources(config)

    assert result["ok"] is False
    assert result["details"]["summary"] == {"total": 2, "passed": 1, "failed": 1}
    assert result["details"]["results"][1]["category"] == "feed_unreachable"


def test_setup_snapshot_exposes_required_fields_and_missing_values(tmp_path, monkeypatch):
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
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    snapshot = _setup_snapshot(config_path, tmp_path)

    assert snapshot["llm"]["missing_fields"] == ["api_key"]
    telegram = snapshot["notifications"]["channels"]["telegram"]
    assert telegram["required_fields"] == ["enabled", "bot_token", "chat_id"]
    assert telegram["missing_fields"] == ["bot_token", "chat_id"]


def test_browser_console_is_read_only_monitor_with_accessible_font_stack():
    html = _index_html()

    assert 'class="skip-link"' in html
    assert (
        '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", '
        '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
    ) in html
    assert "monitoring_console_readonly" in html
    assert 'data-tab="settings"' not in html
    assert "setupForm" not in html
    assert "testLlmButton" not in html
    assert "data-test-target" not in html
    assert "saveSetup" not in html
    assert "required_fields" in html
    assert "missing_fields" in html
    assert "suggested_fix" in html
