from __future__ import annotations

import smtplib
from email.message import EmailMessage
from time import perf_counter

from src.diagnostics import (
    DiagnosticResult,
    classify_smtp_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_email_result,
    is_valid_email_address,
    missing_required_result,
)
from src.models import Alert, EmailSettings, NotificationResult
from src.notifiers.base import Notifier, format_alert_text, format_test_alert_text
from src.secrets import get_env_secret, sanitize_for_log


class EmailNotifier(Notifier):
    name = "Email"

    def __init__(self, settings: EmailSettings):
        self.settings = settings

    def build_message(self, alert: Alert) -> EmailMessage:
        subject = f"[AI News Monitor][{alert.analysis.relevance_score}] {alert.topic_name}: {alert.article.title}"
        return self._build_message(subject, format_alert_text(alert, alert.output_language, alert.mode))

    def build_test_message(self) -> EmailMessage:
        return self._build_message("[AI News Monitor] Test Email", format_test_alert_text(self.name))

    def send(self, alert: Alert) -> NotificationResult:
        validation = self._validate_settings()
        if validation:
            return _notification_from_diagnostic(self.name, validation)
        return self._send_message(self.build_message(alert))

    def send_test(self) -> NotificationResult:
        validation = self._validate_settings()
        if validation:
            return _notification_from_diagnostic(self.name, validation)
        return self._send_message(self.build_test_message())

    def send_test_diagnostic(self) -> DiagnosticResult:
        validation = self._validate_settings()
        if validation:
            return validation
        started = perf_counter()
        username = get_env_secret(self.settings.username_env)
        password = get_env_secret(self.settings.password_env)
        message = self.build_test_message()
        stage = "connect"
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                if self.settings.use_tls:
                    stage = "starttls"
                    smtp.starttls()
                stage = "auth"
                smtp.login(username, password)
                stage = "send"
                smtp.send_message(message)
            return diagnostic_ok(
                "email",
                "Email test notification sent.",
                required_fields=self._required_fields(),
                latency_ms=_latency_ms(started),
                details=self._details(),
            )
        except Exception as exc:  # noqa: BLE001 - user-facing diagnostic
            category = classify_smtp_error(exc, stage=stage)
            return diagnostic_error(
                "email",
                category,
                _smtp_error_message(category),
                technical_detail=exc,
                required_fields=self._required_fields(),
                latency_ms=_latency_ms(started),
                details={**self._details(), "stage": stage},
            )

    def health_check(self) -> NotificationResult:
        validation = self._validate_settings()
        if validation:
            return _notification_from_diagnostic(self.name, validation)
        return NotificationResult(self.name, True)

    def _build_message(self, subject: str, body: str) -> EmailMessage:
        from_addr = get_env_secret(self.settings.from_addr_env)
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_addr
        message["To"] = ", ".join(self.settings.to_addrs)
        message.set_content(body)
        return message

    def _send_message(self, message: EmailMessage) -> NotificationResult:
        validation = self._validate_settings()
        if validation:
            return _notification_from_diagnostic(self.name, validation)
        username = get_env_secret(self.settings.username_env)
        password = get_env_secret(self.settings.password_env)
        stage = "connect"
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                if self.settings.use_tls:
                    stage = "starttls"
                    smtp.starttls()
                stage = "auth"
                smtp.login(username, password)
                stage = "send"
                smtp.send_message(message)
            return NotificationResult(self.name, True)
        except Exception as exc:  # noqa: BLE001 - user-facing channel result
            category = classify_smtp_error(exc, stage=stage)
            return NotificationResult(self.name, False, sanitize_for_log(exc), category)

    def _validate_settings(self) -> DiagnosticResult | None:
        username = get_env_secret(self.settings.username_env)
        password = get_env_secret(self.settings.password_env)
        from_addr = get_env_secret(self.settings.from_addr_env)
        missing = []
        if not self.settings.smtp_host:
            missing.append("smtp_host")
        if not self.settings.smtp_port:
            missing.append("smtp_port")
        if not username:
            missing.append("smtp_username")
        if not password:
            missing.append("smtp_app_password")
        if not from_addr:
            missing.append("from_address")
        if not self.settings.to_addrs:
            missing.append("recipients")
        if missing:
            return missing_required_result("email", missing, required_fields=self._required_fields())
        if not is_valid_email_address(username):
            return invalid_email_result("email", username, field_name="smtp_username")
        if not is_valid_email_address(from_addr):
            return invalid_email_result("email", from_addr, field_name="from_address")
        for recipient in self.settings.to_addrs:
            if not is_valid_email_address(recipient):
                return invalid_email_result("email", recipient, field_name="recipient")
        return None

    def _required_fields(self) -> list[str]:
        return [
            "enabled",
            "smtp_host",
            "smtp_port",
            "starttls",
            "smtp_username",
            "smtp_app_password",
            "from_address",
            "recipients",
        ]

    def _details(self) -> dict[str, object]:
        username = get_env_secret(self.settings.username_env)
        from_addr = get_env_secret(self.settings.from_addr_env)
        warnings = []
        if from_addr and username and from_addr.casefold() != username.casefold():
            warnings.append("From address differs from SMTP username; confirm the provider allows this sender alias.")
        if self.settings.smtp_host == "smtp.gmail.com" and self.settings.smtp_port != 587:
            warnings.append("Gmail usually uses smtp.gmail.com port 587 with STARTTLS.")
        return {
            "smtp_host": self.settings.smtp_host,
            "smtp_port": self.settings.smtp_port,
            "use_tls": self.settings.use_tls,
            "from_matches_username": bool(from_addr and username and from_addr.casefold() == username.casefold()),
            "recipient_count": len(self.settings.to_addrs),
            "warnings": warnings,
        }


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _smtp_error_message(category: str) -> str:
    return {
        "smtp_auth_failed": "SMTP authentication failed.",
        "smtp_starttls_failed": "SMTP STARTTLS failed.",
        "smtp_sender_rejected": "SMTP server rejected the sender address.",
        "smtp_recipient_rejected": "SMTP server rejected at least one recipient.",
        "smtp_connection_timeout": "SMTP connection timed out.",
        "smtp_provider_blocked": "SMTP provider blocked the send attempt.",
        "tls_or_certificate_error": "SMTP TLS or certificate validation failed.",
    }.get(category, "Email test failed.")


def _notification_from_diagnostic(notifier_name: str, result: DiagnosticResult) -> NotificationResult:
    return NotificationResult(
        notifier_name,
        False,
        result.message,
        result.category,
        result.technical_detail,
        result.suggested_fix,
    )
