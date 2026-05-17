from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any
from urllib.parse import urlparse

import httpx

from src.secrets import sanitize_for_log

ERROR_CATEGORIES = (
    "missing_required_field",
    "invalid_url",
    "invalid_email_address",
    "invalid_api_key",
    "model_not_found",
    "unsupported_model_api",
    "base_url_unreachable",
    "api_auth_failed",
    "api_rate_limited",
    "api_bad_response",
    "api_timeout",
    "query_too_long",
    "unsupported_query_shape",
    "invalid_encoded_query",
    "tls_or_certificate_error",
    "network_unreachable",
    "proxy_or_firewall_issue",
    "smtp_auth_failed",
    "smtp_starttls_failed",
    "smtp_sender_rejected",
    "smtp_recipient_rejected",
    "smtp_connection_timeout",
    "smtp_provider_blocked",
    "webhook_unreachable",
    "webhook_http_error",
    "webhook_auth_failed",
    "feed_unreachable",
    "feed_parse_failed",
    "feed_empty",
    "source_language_unsupported",
    "local_server_port_in_use",
    "sse_connection_failed",
    "unknown_error",
)

SUGGESTED_FIXES = {
    "missing_required_field": "Fill the required field, save settings, then run the test again.",
    "invalid_url": "Use a complete HTTP or HTTPS URL, for example https://example.com/feed.xml.",
    "invalid_email_address": "Use a valid email address such as name@example.com.",
    "invalid_api_key": "Check that the API key is copied from the provider console and has not expired.",
    "model_not_found": "Check the model name in your provider console, or choose a model supported by the base URL.",
    "unsupported_model_api": "Use an OpenAI-compatible chat completions endpoint or change the base URL/model.",
    "base_url_unreachable": "Check the base URL, internet connection, VPN, proxy, and provider status.",
    "api_auth_failed": "Check provider credentials and account permissions.",
    "api_rate_limited": "Wait and retry, or lower polling frequency and review provider rate limits.",
    "api_bad_response": "The provider returned an unexpected response. Check status, content type, and response preview.",
    "api_timeout": "Retry later, increase timeout, or check whether the network/provider is slow.",
    "query_too_long": "Reduce keywords, use fewer OR terms, or use a simpler source query.",
    "unsupported_query_shape": "Simplify the source query and avoid unsupported operators.",
    "invalid_encoded_query": "Check URL encoding and remove malformed query characters.",
    "tls_or_certificate_error": "Check system time, certificate trust, proxy inspection, and HTTPS settings.",
    "network_unreachable": "Check internet access, DNS, firewall, VPN, or proxy settings.",
    "proxy_or_firewall_issue": "Check proxy and firewall rules for this provider endpoint.",
    "smtp_auth_failed": "Use a Gmail app password or provider-specific SMTP password; do not use your normal login password.",
    "smtp_starttls_failed": "Use port 587 with STARTTLS, or check whether the provider requires a different TLS setting.",
    "smtp_sender_rejected": "Make the From address match the authenticated sender or an allowed alias.",
    "smtp_recipient_rejected": "Check recipient addresses and provider sending policy.",
    "smtp_connection_timeout": "Check SMTP host, port, firewall, VPN, and whether port 587 is blocked.",
    "smtp_provider_blocked": "Check provider security alerts, app-password access, and organization mail policy.",
    "webhook_unreachable": "Check the webhook URL, provider status, network, and firewall/proxy settings.",
    "webhook_http_error": "Check the webhook URL, expected method, headers, payload, and provider response.",
    "webhook_auth_failed": "Regenerate the webhook URL or token and save it locally.",
    "feed_unreachable": "Open the feed URL in a browser and check whether the source is public and available.",
    "feed_parse_failed": "Use a valid RSS or Atom feed URL, not a normal web page.",
    "feed_empty": "Use a feed that currently publishes at least one item.",
    "source_language_unsupported": "Use English or Simplified Chinese sources, or change the source language.",
    "local_server_port_in_use": "Choose a different local server port or stop the process using the current port.",
    "sse_connection_failed": "Refresh the browser console and check that the local server is still running.",
    "unknown_error": "Review the technical detail, then retry or check the local logs.",
}


@dataclass
class DiagnosticResult:
    target: str
    ok: bool
    message: str
    category: str | None = None
    suggested_fix: str | None = None
    technical_detail: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    configured: bool = True
    enabled: bool = True
    tested_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    latency_ms: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "target": self.target,
            "message": self.message,
            "category": self.category,
            "suggested_fix": self.suggested_fix,
            "technical_detail": self.technical_detail,
            "missing_fields": self.missing_fields,
            "required_fields": self.required_fields,
            "configured": self.configured,
            "enabled": self.enabled,
            "tested_at": self.tested_at,
            "latency_ms": self.latency_ms,
            "details": self.details,
        }


def diagnostic_ok(
    target: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    required_fields: list[str] | None = None,
    latency_ms: int | None = None,
    enabled: bool = True,
) -> DiagnosticResult:
    return DiagnosticResult(
        target=target,
        ok=True,
        message=message,
        required_fields=required_fields or [],
        details=details or {},
        latency_ms=latency_ms,
        enabled=enabled,
    )


def diagnostic_error(
    target: str,
    category: str,
    message: str,
    *,
    technical_detail: object | None = None,
    suggested_fix: str | None = None,
    missing_fields: list[str] | None = None,
    required_fields: list[str] | None = None,
    configured: bool | None = None,
    enabled: bool = True,
    latency_ms: int | None = None,
    details: dict[str, Any] | None = None,
) -> DiagnosticResult:
    if category not in ERROR_CATEGORIES:
        category = "unknown_error"
    missing = missing_fields or []
    return DiagnosticResult(
        target=target,
        ok=False,
        category=category,
        message=message,
        suggested_fix=suggested_fix or SUGGESTED_FIXES[category],
        technical_detail=redact_detail(technical_detail),
        missing_fields=missing,
        required_fields=required_fields or [],
        configured=bool(configured) if configured is not None else not missing,
        enabled=enabled,
        latency_ms=latency_ms,
        details=details or {},
    )


def missing_required_result(
    target: str,
    missing_fields: list[str],
    *,
    required_fields: list[str] | None = None,
    enabled: bool = True,
) -> DiagnosticResult:
    names = ", ".join(missing_fields)
    return diagnostic_error(
        target,
        "missing_required_field",
        f"Missing required field: {names}.",
        missing_fields=missing_fields,
        required_fields=required_fields or missing_fields,
        configured=False,
        enabled=enabled,
    )


def redact_detail(value: object | None) -> str | None:
    if value is None:
        return None
    return sanitize_for_log(value)


def is_valid_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_valid_email_address(value: str) -> bool:
    address = parseaddr(str(value or "").strip())[1]
    if not address or address != str(value or "").strip():
        return False
    local, _, domain = address.partition("@")
    return bool(local and domain and "." in domain and " " not in address)


def invalid_url_result(target: str, url: str, *, required_fields: list[str] | None = None) -> DiagnosticResult:
    return diagnostic_error(
        target,
        "invalid_url",
        "URL is not a valid HTTP or HTTPS URL.",
        technical_detail=url,
        required_fields=required_fields or [],
    )


def invalid_email_result(target: str, email: str, *, field_name: str = "email address") -> DiagnosticResult:
    return diagnostic_error(
        target,
        "invalid_email_address",
        f"Invalid {field_name}.",
        technical_detail=email,
        required_fields=[field_name],
    )


def classify_llm_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "api_timeout"
    if isinstance(exc, httpx.ProxyError):
        return "proxy_or_firewall_issue"
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        detail = exc.response.text.casefold()
        if status_code in {401, 403}:
            return "invalid_api_key"
        if status_code == 404:
            return "model_not_found"
        if status_code == 429:
            return "api_rate_limited"
        if status_code == 400 and ("model" in detail or "response_format" in detail or "chat" in detail):
            return "unsupported_model_api"
        if 500 <= status_code:
            return "base_url_unreachable"
        return "api_auth_failed" if status_code in {400, 401, 403} else "unknown_error"
    return _network_category(exc, default="base_url_unreachable")


def classify_webhook_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "api_timeout"
    if isinstance(exc, httpx.ProxyError):
        return "proxy_or_firewall_issue"
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in {401, 403}:
            return "webhook_auth_failed"
        return "webhook_http_error"
    return _network_category(exc, default="webhook_unreachable")


def classify_feed_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "api_timeout"
    if isinstance(exc, httpx.ProxyError):
        return "proxy_or_firewall_issue"
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 429:
            return "api_rate_limited"
        if status_code in {408, 504}:
            return "api_timeout"
        if 500 <= status_code:
            return "base_url_unreachable"
        if status_code in {400, 414, 422}:
            return "api_bad_response"
        return "feed_unreachable"
    return _network_category(exc, default="feed_unreachable")


def classify_smtp_error(exc: BaseException, *, stage: str | None = None) -> str:
    import smtplib

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "smtp_auth_failed"
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "smtp_sender_rejected"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "smtp_recipient_rejected"
    if isinstance(exc, (TimeoutError, socket.timeout, smtplib.SMTPConnectError)):
        return "smtp_connection_timeout"
    if isinstance(exc, ssl.SSLError):
        return "tls_or_certificate_error"
    if stage == "auth":
        return "smtp_auth_failed"
    if stage == "starttls":
        return "smtp_starttls_failed"
    if stage == "send":
        return "smtp_provider_blocked"
    if isinstance(exc, (smtplib.SMTPNotSupportedError, smtplib.SMTPHeloError)):
        return "smtp_starttls_failed"
    text = str(exc).casefold()
    if any(marker in text for marker in ("blocked", "less secure", "application-specific", "app password")):
        return "smtp_provider_blocked"
    if any(marker in text for marker in ("timed out", "timeout")):
        return "smtp_connection_timeout"
    return "unknown_error"


def _network_category(exc: httpx.HTTPError, *, default: str) -> str:
    text = str(exc).casefold()
    if any(marker in text for marker in ("certificate", "ssl", "tls")):
        return "tls_or_certificate_error"
    if any(marker in text for marker in ("proxy", "firewall")):
        return "proxy_or_firewall_issue"
    if any(marker in text for marker in ("name or service", "nodename", "dns", "network", "connection refused")):
        return "network_unreachable"
    return default
