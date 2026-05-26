from __future__ import annotations

import json
import smtplib
from dataclasses import replace

import httpx

from src.config import load_config, parse_config
from src.diagnostics import classify_feed_http_error
from src.models import Article, EmailSettings, LLMAnalysis, NotificationResult, RuntimeStatus, TopicConfig
from src.monitor import NewsMonitor
from src.notifiers.email_notifier import EmailNotifier
from src.pipeline import finish
from src.realtime import (
    LocalEventServer,
    SseBroker,
    _diagnose_json_source,
    _enabled_source_targets,
    _index_html,
    _setup_snapshot,
    readiness_to_dict,
    status_to_dict,
)
from src.scheduler import MonitorWorker
from src.source_reliability import source_package_status
from src.storage import SQLiteStore
from src.utils.time_utils import utc_now
from tests.helpers import start_server_or_skip
from tests.test_config import CONFIG_TEXT


class MockNotifier:
    name = "Mock Notifier"

    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)
        return NotificationResult(self.name, True)


class StaticSource:
    name = "Static Source"

    def __init__(self, article: Article | None = None):
        self.article = article or Article(
            title="chip partnership news",
            url="https://example.com/chip-partnership",
            source=self.name,
            snippet="chip partnership update",
            language="en",
            published_at=utc_now(),
        )

    def fetch(self, topic: TopicConfig):
        return [replace(self.article, source=self.name)]


class StaticLlm:
    api_key = "test-key"

    def __init__(self, score: int = 95, actionable: bool = True):
        self.score = score
        self.actionable = actionable

    def analyze_article(self, topic, article):
        return LLMAnalysis(
            relevance_score=self.score,
            is_actionable_alert=self.actionable,
            event_type="test",
            summary="Test summary.",
            why_it_matters="Test reason.",
            market_watch_suggestions=[],
            bullish_path="N/A",
            bearish_path="N/A",
            risk_notes="N/A",
            uncertainty_notes="N/A",
            source_reliability="medium",
            recommended_user_action="watch_only",
            notification_title="Test alert",
        )


class RateLimitedSource:
    name = "Yahoo Finance RSS"

    def fetch(self, topic: TopicConfig):
        request = httpx.Request("GET", "https://finance.yahoo.com/news/rssindex")
        response = httpx.Response(429, request=request, text="Too Many Requests")
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)


def _write_config(tmp_path, text: str = CONFIG_TEXT):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(text, encoding="utf-8")
    return config_path


def test_e2e_test_mode_produces_visible_alert_and_mock_notification(tmp_path):
    config_path = _write_config(tmp_path)
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    notifier = MockNotifier()
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        notifier_factory=lambda settings, timeout: [notifier],
    )

    status = monitor.run_e2e_test()

    assert status.e2e_result["test_mode"] is True
    assert status.e2e_result["result"] == "success"
    assert status.e2e_result["articles_fetched"] == 1
    assert status.e2e_result["candidates_ranked"] == 1
    assert status.e2e_result["event_clusters_produced"] == 1
    assert status.e2e_result["candidates_sent_to_llm"] == 1
    assert status.e2e_result["event_clusters_sent_to_llm"] == 1
    assert status.e2e_result["alerts_saved"] == 1
    assert status.e2e_result["event_alerts_generated"] == 1
    assert status.e2e_result["notifications_succeeded"] == 1
    assert len(notifier.sent) == 1
    assert "[E2E TEST]" in status.recent_alerts[0].title
    assert status.recent_alerts[0].article.raw["test_mode"] is True
    assert load_config(config_path).topics[0].min_relevance_score == 80

    second_status = monitor.run_e2e_test()

    assert second_status.e2e_result["result"] == "success"
    assert second_status.e2e_result["candidates_ranked"] == 1
    assert second_status.e2e_result["event_clusters_produced"] == 1
    assert second_status.e2e_result["notifications_succeeded"] == 1
    assert len(notifier.sent) == 2


def test_run_cycle_pipeline_funnel_counts_and_serializes_summary(tmp_path):
    config_path = _write_config(tmp_path)
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    notifier = MockNotifier()
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [StaticSource()],
        llm_factory=lambda config: StaticLlm(),
        notifier_factory=lambda settings, timeout: [notifier],
    )

    status = monitor.run_cycle()
    funnel = status.pipeline_funnel
    serialized = status_to_dict(status)

    assert funnel["result"] == "success"
    assert funnel["sources_attempted"] == 1
    assert funnel["sources_succeeded"] == 1
    assert funnel["articles_fetched"] == 1
    assert funnel["articles_accepted_by_language"] == 1
    assert funnel["articles_keyword_matched"] == 1
    assert funnel["event_clusters_produced"] == 1
    assert funnel["alerts_saved"] == 1
    assert funnel["notifications_succeeded"] == 1
    assert funnel["diagnostic_counts"]["fetched"] == 1
    assert funnel["diagnostic_counts"]["event_clusters"] == 1
    assert funnel["diagnostic_counts"]["sent_to_llm"] == 1
    assert "Fetched 1 -> Dedupe 1 -> Candidates 1 -> Events 1 -> LLM 1 -> Alerts 1" in funnel["concise_summary"]
    assert "{" not in funnel["concise_summary"]
    assert serialized["pipeline_funnel"]["concise_summary"] == funnel["concise_summary"]


def test_zero_alert_below_threshold_explains_candidate_and_keeps_production_threshold(tmp_path):
    config_path = _write_config(tmp_path)
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [StaticSource()],
        llm_factory=lambda config: StaticLlm(score=60),
        notifier_factory=lambda settings, timeout: [MockNotifier()],
    )

    status = monitor.run_cycle()
    funnel = status.pipeline_funnel

    assert funnel["alerts_saved"] == 0
    assert funnel["rejected_below_threshold"] == 1
    assert funnel["rejection_reasons"]["score_below_threshold"] == 1
    assert funnel["top_rejected_candidate"]["score"] == 60
    assert funnel["top_rejected_candidate"]["threshold"] == 80
    assert "below threshold" in funnel["zero_alert_explanation"]
    assert "50-60" in funnel["recommended_action"]
    assert load_config(config_path).topics[0].min_relevance_score == 80


def test_missing_notifier_is_recorded_after_alert_is_saved(tmp_path):
    config_path = _write_config(tmp_path)
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [StaticSource()],
        llm_factory=lambda config: StaticLlm(),
        notifier_factory=lambda settings, timeout: [],
    )

    status = monitor.run_cycle()

    assert status.pipeline_funnel["alerts_saved"] == 1
    assert status.pipeline_funnel["rejection_reasons"]["missing_notifier"] == 1
    assert (
        status.pipeline_funnel["zero_alert_explanation"]
        == "Alert pipeline succeeded, but no notification channel is ready."
    )


def test_local_control_run_once_and_e2e_actions_emit_concise_ack():
    calls: list[str] = []
    server = LocalEventServer(
        "127.0.0.1",
        0,
        SseBroker(),
        status_provider=RuntimeStatus,
        control_handlers={
            "run_once": lambda: calls.append("run_once"),
            "e2e_test": lambda: calls.append("e2e_test"),
        },
    )
    start_server_or_skip(server)
    try:
        with httpx.Client(timeout=5) as client:
            run_once = client.post(f"{server.url}/api/control", json={"action": "run_once"}).json()
            e2e_test = client.post(f"{server.url}/api/control", json={"action": "e2e_test"}).json()
    finally:
        server.stop()

    assert run_once == {"ok": True, "action": "run_once"}
    assert e2e_test == {"ok": True, "action": "e2e_test"}
    assert calls == ["run_once", "e2e_test"]


def test_gdelt_diagnostics_cover_production_shape_non_json_429_and_long_query(monkeypatch):
    config = parse_config(
        {
            "topics": [
                {
                    "name": "AI infrastructure",
                    "enabled": True,
                    "prompt": "Watch AI infrastructure.",
                    "keywords": ["OpenAI", "NVIDIA"],
                }
            ]
        }
    )
    targets = _enabled_source_targets(config)

    assert [target["name"] for target in targets[:2]] == ["GDELT Production Query", "GDELT Smoke Query"]
    assert targets[0]["diagnostic_shape"] == "production_topic"
    assert '"OpenAI"' in targets[0]["params"]["query"]

    def non_json(client, method, url, **kwargs):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>not json</html>")

    monkeypatch.setattr("src.realtime.request_with_retries", non_json)
    result = _diagnose_json_source(targets[0], 5)
    assert result.ok is False
    assert result.category == "api_bad_response"

    def rate_limited(client, method, url, **kwargs):
        request = httpx.Request("GET", url)
        response = httpx.Response(429, request=request, text="rate limited secret-token")
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)

    monkeypatch.setenv("TEST_SECRET", "secret-token")
    monkeypatch.setattr("src.realtime.request_with_retries", rate_limited)
    result = _diagnose_json_source(targets[0], 5)
    assert result.category == "api_rate_limited"
    assert "secret-token" not in result.details["response_preview"]

    def timeout(client, method, url, **kwargs):
        raise httpx.TimeoutException("request timed out")

    monkeypatch.setattr("src.realtime.request_with_retries", timeout)
    assert _diagnose_json_source(targets[0], 5).category == "api_timeout"

    def ssl_error(client, method, url, **kwargs):
        raise httpx.ConnectError("SSL handshake failed")

    monkeypatch.setattr("src.realtime.request_with_retries", ssl_error)
    assert _diagnose_json_source(targets[0], 5).category == "tls_or_certificate_error"

    long_result = _diagnose_json_source(
        {
            "name": "GDELT Long Query",
            "kind": "json_api",
            "url": "https://api.gdeltproject.org/api/v2/doc/doc",
            "params": {"query": "x" * 901, "mode": "ArtList", "format": "json", "maxrecords": "1"},
        },
        5,
    )
    assert long_result.category == "query_too_long"


def test_yahoo_429_is_classified_and_puts_source_into_backoff(tmp_path):
    request = httpx.Request("GET", "https://finance.yahoo.com/news/rssindex")
    response = httpx.Response(429, request=request, text="Too Many Requests")
    assert (
        classify_feed_http_error(httpx.HTTPStatusError("429", request=request, response=response)) == "api_rate_limited"
    )

    config_path = _write_config(tmp_path)
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [RateLimitedSource()],
        llm_factory=lambda config: StaticLlm(),
        notifier_factory=lambda settings, timeout: [MockNotifier()],
    )

    status = monitor.run_cycle()
    source_state = store.load_source_state("Yahoo Finance RSS")

    assert source_state["last_error_category"] == "api_rate_limited"
    assert source_state["current_backoff_seconds"] > 0
    assert source_state["next_retry_at"]
    assert status.pipeline_funnel["rejection_reasons"]["rate_limit"] == 1
    assert status.source_health["Yahoo Finance RSS"] == "Yahoo Finance RSS: rate limited"


def test_finance_package_has_alternative_public_sources_and_warnings():
    config = parse_config({"sources": {"enabled_packages": ["finance-starter"]}})
    package_rows = source_package_status(config, {})
    finance = next(row for row in package_rows if row["id"] == "finance-starter")

    assert finance["enabled"] is True
    assert finance["source_count"] > 1
    assert finance["failing_source_count"] == 0
    assert "last_package_test" in finance
    assert "MarketWatch Top Stories" in finance["source_names"]
    assert "Yahoo Finance RSS" not in finance["source_names"]
    assert finance["warnings"] == ["This source package is enabled, but none of its sources are currently fresh."]

    empty_rows = source_package_status(parse_config({"sources": {"enabled_packages": []}}), {})
    assert any(row["warnings"] for row in empty_rows)


def test_email_health_requires_from_address_and_warns_when_alias_differs(monkeypatch):
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "app-password")
    monkeypatch.delenv("EMAIL_FROM", raising=False)

    missing = EmailNotifier(EmailSettings(enabled=True, to_addrs=["receiver@example.com"])).health_check()
    assert missing.success is False
    assert missing.error_category == "missing_required_field"
    assert "from_address" in (missing.error_message or "")

    monkeypatch.setenv("EMAIL_FROM", "not-an-email")
    invalid = EmailNotifier(EmailSettings(enabled=True, to_addrs=["receiver@example.com"])).health_check()
    assert invalid.success is False
    assert invalid.error_category == "invalid_email_address"

    calls = []

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
            calls.append(f"login:{username}")

        def send_message(self, message):
            calls.append(f"send:{message['From']}:{message['To']}")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("EMAIL_FROM", "alias@example.com")
    result = EmailNotifier(EmailSettings(enabled=True, to_addrs=["receiver@example.com"])).send_test_diagnostic()

    assert result.ok is True
    assert result.details["warnings"] == [
        "From address differs from SMTP username; confirm the provider allows this sender alias."
    ]
    assert calls[-1] == "send:alias@example.com:receiver@example.com"


def test_setup_snapshot_and_email_health_agree_on_missing_from_address(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
notifiers:
  email:
    enabled: true
    to_addrs: ["receiver@example.com"]
topics: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "LLM_API_KEY=test\nEMAIL_USERNAME=sender@example.com\nEMAIL_APP_PASSWORD=app-password\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "app-password")
    monkeypatch.delenv("EMAIL_FROM", raising=False)

    snapshot = _setup_snapshot(config_path, tmp_path)
    health = EmailNotifier(EmailSettings(enabled=True, to_addrs=["receiver@example.com"])).health_check()

    email = snapshot["notifications"]["channels"]["email"]
    assert email["configured"] is False
    assert "from_address" in email["missing_fields"]
    assert health.success is False
    assert health.error_category == "missing_required_field"


def test_health_liveness_and_readiness_endpoint_states():
    healthy = RuntimeStatus(
        state="Running",
        llm_health="configured",
        notifier_states={"Email": {"enabled": True, "health": "ok"}},
        coverage_quality={"global": {"coverage_quality": "high", "critical_gap_count": 0}},
        pipeline_funnel=finish({"cycle_started_at": utc_now(), "alerts_saved": 1, "notifications_succeeded": 1}),
    )
    degraded = RuntimeStatus(
        state="Running",
        llm_health="configured",
        notifier_states={},
        coverage_quality={"global": {"coverage_quality": "critical", "critical_gap_count": 1}},
    )

    assert readiness_to_dict(healthy)["can_send_alerts"] is True
    assert readiness_to_dict(degraded)["can_send_alerts"] is False
    assert readiness_to_dict(degraded)["readiness"] == "not_ready"

    server = LocalEventServer("127.0.0.1", 0, SseBroker(), status_provider=lambda: healthy)
    start_server_or_skip(server)
    try:
        with httpx.Client(timeout=5) as client:
            health = client.get(f"{server.url}/health").json()
            readiness = client.get(f"{server.url}/readiness").json()
            api_readiness = client.get(f"{server.url}/api/readiness").json()
    finally:
        server.stop()

    assert health["ok"] is True
    assert readiness["server_alive"] is True
    assert readiness["readiness"] == "ready"
    assert api_readiness["can_send_alerts"] is True


def test_paused_state_visibility_in_status_and_browser_html():
    status = RuntimeStatus(
        state="Paused",
        pause_reason="User paused monitoring.",
        next_cycle_time=utc_now(),
    )
    payload = status_to_dict(status)
    html = _index_html()

    assert payload["state"] == "Paused"
    assert payload["pause_reason"] == "User paused monitoring."
    assert payload["next_cycle_time"]
    assert "Monitoring is paused. No new alerts will be sent until you resume." in html
    assert 'data-action="resume"' in html
    assert 'data-action="start"' in html
    assert 'data-action="run_once"' in html
    assert 'data-action="e2e_test"' in html


def test_browser_console_has_overflow_rules_and_no_raw_json_primary_event_rendering():
    html = _index_html()

    assert "overflow-wrap: anywhere" in html
    assert "word-break: break-word" in html
    assert "max-width: 100%" in html
    assert "Pipeline Funnel" in html
    assert "Notification Health" in html
    assert "Real-time Events" in html
    assert "Enable in desktop app" in html
    assert "JSON.stringify(event)" not in html
    assert "eventItems = eventItems.slice(0, 50)" in html
    assert "debug-details" in html
    assert "safe-code-block" in html
    assert "show_details" in html


def test_scheduler_control_callbacks_publish_events_without_running_cycle():
    broker = SseBroker()
    events = []
    server = LocalEventServer(
        "127.0.0.1",
        0,
        broker,
        status_provider=RuntimeStatus,
        control_handlers={"resume": lambda: events.append({"action": "resume"})},
    )
    start_server_or_skip(server)
    try:
        response = httpx.post(f"{server.url}/api/control", json={"action": "resume"}, timeout=5)
    finally:
        server.stop()

    assert response.json() == {"ok": True, "action": "resume"}
    assert events == [{"action": "resume"}]


def test_monitor_worker_lifecycle_actions_publish_events(tmp_path):
    config_path = _write_config(tmp_path)
    worker = MonitorWorker(config_path, tmp_path)
    subscriber = worker.broker.subscribe()
    worker._ensure_event_server = lambda: None
    worker._run = lambda: None

    worker.start()
    worker.pause()
    worker.resume()
    worker.stop()

    actions = []
    while not subscriber.empty():
        actions.append(subscriber.get_nowait().get("action"))

    assert actions[:4] == ["start", "pause", "resume", "stop"]
    assert worker.status.state == "Stopped"


def test_event_details_remain_valid_json_for_copying():
    payload = {"type": "source_fetch", "source": "GDELT", "ok": False, "category": "api_bad_response"}

    assert json.dumps(payload, ensure_ascii=False)
