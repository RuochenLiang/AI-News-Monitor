from __future__ import annotations

import json
from time import perf_counter

import httpx

from src.diagnostics import (
    DiagnosticResult,
    classify_webhook_http_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_url_result,
    is_valid_http_url,
    missing_required_result,
)
from src.models import Alert, GenericWebhookSettings, NotificationResult
from src.notifiers.base import Notifier, format_test_alert_text
from src.secrets import get_env_secret, sanitize_for_log
from src.utils.http_utils import request_with_retries


class GenericWebhookNotifier(Notifier):
    name = "Generic Webhook"

    def __init__(self, settings: GenericWebhookSettings, timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self.client = client

    def build_payload(self, alert: Alert) -> dict:
        if self.settings.body_template and self.settings.body_template != "default":
            template = self.settings.body_template
            rendered = template.format(
                title=alert.title,
                topic=alert.topic_name,
                relevance_score=alert.analysis.relevance_score,
                summary=alert.analysis.summary,
                link=alert.article.url,
            )
            try:
                return json.loads(rendered)
            except json.JSONDecodeError:
                return {"body": rendered}
        return {
            "title": alert.title,
            "topic": alert.topic_name,
            "relevance_score": alert.analysis.relevance_score,
            "summary": alert.analysis.summary,
            "links": alert.links,
        }

    def send(self, alert: Alert) -> NotificationResult:
        return self._send_payload(self.build_payload(alert))

    def send_test(self) -> NotificationResult:
        return self._send_payload({"title": "AI News Monitor Test", "summary": format_test_alert_text(self.name)})

    def send_test_diagnostic(self) -> DiagnosticResult:
        required_fields = ["enabled", "url", "method"]
        url = get_env_secret(self.settings.url_env)
        if not url:
            return missing_required_result("generic_webhook", ["url"], required_fields=required_fields)
        if not is_valid_http_url(url):
            return invalid_url_result("generic_webhook", url, required_fields=required_fields)
        started = perf_counter()
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(
                client,
                self.settings.method or "POST",
                url,
                headers=self.settings.headers,
                json={"title": "AI News Monitor Test", "summary": format_test_alert_text(self.name)},
            )
            return diagnostic_ok(
                "generic_webhook",
                "Generic Webhook test notification sent.",
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details={"method": self.settings.method or "POST"},
            )
        except httpx.HTTPError as exc:
            category = classify_webhook_http_error(exc)
            return diagnostic_error(
                "generic_webhook",
                category,
                _webhook_error_message(category),
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details={"method": self.settings.method or "POST"},
            )
        finally:
            if close_client:
                client.close()

    def health_check(self) -> NotificationResult:
        if not get_env_secret(self.settings.url_env):
            return NotificationResult(self.name, False, "Generic webhook URL is missing.", "missing_required_field")
        return NotificationResult(self.name, True)

    def _send_payload(self, payload: dict) -> NotificationResult:
        url = get_env_secret(self.settings.url_env)
        if not url:
            return NotificationResult(self.name, False, "Generic webhook URL is missing.", "missing_required_field")
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(
                client, self.settings.method or "POST", url, headers=self.settings.headers, json=payload
            )
            return NotificationResult(self.name, True)
        except httpx.HTTPError as exc:
            return NotificationResult(self.name, False, sanitize_for_log(exc), classify_webhook_http_error(exc))
        finally:
            if close_client:
                client.close()


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _webhook_error_message(category: str) -> str:
    return {
        "webhook_auth_failed": "Generic webhook authentication failed.",
        "webhook_http_error": "Generic webhook returned an HTTP error.",
        "webhook_unreachable": "Generic webhook is unreachable.",
        "api_timeout": "Generic webhook request timed out.",
        "network_unreachable": "Network is unreachable for the generic webhook.",
        "proxy_or_firewall_issue": "Proxy or firewall blocked the generic webhook.",
    }.get(category, "Generic webhook test failed.")
