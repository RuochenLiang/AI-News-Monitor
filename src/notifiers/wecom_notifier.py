from __future__ import annotations

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
from src.models import Alert, NotificationResult, WebhookSettings
from src.notifiers.base import Notifier, format_alert_text, format_test_alert_text
from src.secrets import get_env_secret, sanitize_for_log
from src.utils.http_utils import request_with_retries


class WeComNotifier(Notifier):
    name = "WeCom"

    def __init__(self, settings: WebhookSettings, timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self.client = client

    def send(self, alert: Alert) -> NotificationResult:
        return self._send_text(format_alert_text(alert, alert.output_language, alert.mode))

    def send_test(self) -> NotificationResult:
        return self._send_text(format_test_alert_text(self.name))

    def send_test_diagnostic(self) -> DiagnosticResult:
        required_fields = ["enabled", "webhook_url"]
        url = get_env_secret(self.settings.webhook_url_env)
        if not url:
            return missing_required_result("wecom", ["webhook_url"], required_fields=required_fields)
        if not is_valid_http_url(url):
            return invalid_url_result("wecom", url, required_fields=required_fields)
        started = perf_counter()
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(
                client,
                "POST",
                url,
                json={"msgtype": "markdown", "markdown": {"content": format_test_alert_text(self.name)}},
            )
            return diagnostic_ok(
                "wecom",
                "WeCom test notification sent.",
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
            )
        except httpx.HTTPError as exc:
            category = classify_webhook_http_error(exc)
            return diagnostic_error(
                "wecom",
                category,
                _webhook_error_message("WeCom", category),
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
            )
        finally:
            if close_client:
                client.close()

    def health_check(self) -> NotificationResult:
        if not get_env_secret(self.settings.webhook_url_env):
            return NotificationResult(self.name, False, "WeCom webhook URL is missing.", "missing_required_field")
        return NotificationResult(self.name, True)

    def _send_text(self, text: str) -> NotificationResult:
        url = get_env_secret(self.settings.webhook_url_env)
        if not url:
            return NotificationResult(self.name, False, "WeCom webhook URL is missing.", "missing_required_field")
        payload = {"msgtype": "markdown", "markdown": {"content": text}}
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(client, "POST", url, json=payload)
            return NotificationResult(self.name, True)
        except httpx.HTTPError as exc:
            return NotificationResult(self.name, False, sanitize_for_log(exc), classify_webhook_http_error(exc))
        finally:
            if close_client:
                client.close()


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _webhook_error_message(name: str, category: str) -> str:
    return {
        "webhook_auth_failed": f"{name} webhook authentication failed.",
        "webhook_http_error": f"{name} webhook returned an HTTP error.",
        "webhook_unreachable": f"{name} webhook is unreachable.",
        "api_timeout": f"{name} webhook request timed out.",
        "network_unreachable": f"Network is unreachable for {name}.",
        "proxy_or_firewall_issue": f"Proxy or firewall blocked {name}.",
    }.get(category, f"{name} webhook test failed.")
