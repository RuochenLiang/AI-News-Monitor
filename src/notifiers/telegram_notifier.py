from __future__ import annotations

from time import perf_counter

import httpx

from src.diagnostics import (
    DiagnosticResult,
    classify_webhook_http_error,
    diagnostic_error,
    diagnostic_ok,
    missing_required_result,
)
from src.models import Alert, NotificationResult, TelegramSettings
from src.notifiers.base import Notifier, format_alert_text, format_test_alert_text
from src.secrets import get_env_secret, sanitize_for_log
from src.utils.http_utils import request_with_retries


class TelegramNotifier(Notifier):
    name = "Telegram"

    def __init__(self, settings: TelegramSettings, timeout_seconds: int = 20, client: httpx.Client | None = None):
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self.client = client

    def send(self, alert: Alert) -> NotificationResult:
        return self._send_text(format_alert_text(alert, alert.output_language, alert.mode))

    def send_test(self) -> NotificationResult:
        return self._send_text(format_test_alert_text(self.name))

    def send_test_diagnostic(self) -> DiagnosticResult:
        token = get_env_secret(self.settings.bot_token_env)
        chat_id = get_env_secret(self.settings.chat_id_env)
        required_fields = ["enabled", "bot_token", "chat_id"]
        missing = []
        if not token:
            missing.append("bot_token")
        if not chat_id:
            missing.append("chat_id")
        if missing:
            return missing_required_result("telegram", missing, required_fields=required_fields)
        started = perf_counter()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": format_test_alert_text(self.name), "disable_web_page_preview": False}
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(client, "POST", url, data=payload)
            return diagnostic_ok(
                "telegram",
                "Telegram test notification sent.",
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details={"chat_id_configured": True},
            )
        except httpx.HTTPStatusError as exc:
            category = "invalid_api_key" if exc.response.status_code in {401, 403} else classify_webhook_http_error(exc)
            return diagnostic_error(
                "telegram",
                category,
                _telegram_error_message(category),
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
            )
        except httpx.HTTPError as exc:
            category = classify_webhook_http_error(exc)
            return diagnostic_error(
                "telegram",
                category,
                _telegram_error_message(category),
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
            )
        finally:
            if close_client:
                client.close()

    def health_check(self) -> NotificationResult:
        token = get_env_secret(self.settings.bot_token_env)
        chat_id = get_env_secret(self.settings.chat_id_env)
        if not token or not chat_id:
            return NotificationResult(
                self.name, False, "Telegram token or chat ID is missing.", "missing_required_field"
            )
        return NotificationResult(self.name, True)

    def _send_text(self, text: str) -> NotificationResult:
        token = get_env_secret(self.settings.bot_token_env)
        chat_id = get_env_secret(self.settings.chat_id_env)
        if not token or not chat_id:
            return NotificationResult(
                self.name, False, "Telegram token or chat ID is missing.", "missing_required_field"
            )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": False}
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            request_with_retries(client, "POST", url, data=payload)
            return NotificationResult(self.name, True)
        except httpx.HTTPError as exc:
            category = (
                "invalid_api_key"
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {401, 403}
                else classify_webhook_http_error(exc)
            )
            return NotificationResult(self.name, False, sanitize_for_log(exc), category)
        finally:
            if close_client:
                client.close()


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _telegram_error_message(category: str) -> str:
    return {
        "missing_required_field": "Telegram token or chat ID is missing.",
        "invalid_api_key": "Telegram bot token was rejected.",
        "webhook_auth_failed": "Telegram request was rejected.",
        "webhook_http_error": "Telegram API returned an HTTP error.",
        "api_timeout": "Telegram request timed out.",
        "network_unreachable": "Network is unreachable for Telegram.",
        "proxy_or_firewall_issue": "Proxy or firewall blocked Telegram.",
    }.get(category, "Telegram test failed.")
