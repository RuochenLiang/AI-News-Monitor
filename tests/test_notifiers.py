from __future__ import annotations

from src.models import EmailSettings, GenericWebhookSettings, NotifierSettings
from src.monitor import build_notifiers
from src.notifiers.base import DISCLAIMER, format_alert_text
from src.notifiers.email_notifier import EmailNotifier
from src.notifiers.generic_webhook_notifier import GenericWebhookNotifier
from src.sample_data import sample_alert


def test_email_payload_formatting_without_sending(monkeypatch):
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    settings = EmailSettings(enabled=True, to_addrs=["to@example.com"])
    message = EmailNotifier(settings).build_message(sample_alert())

    assert "AI News Monitor" in message["Subject"]
    assert "to@example.com" in message["To"]
    assert DISCLAIMER in message.get_content()
    assert "App Password" not in message.get_content()


def test_email_alert_contains_summary_suggestions_action_and_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    alert = sample_alert()
    alert.mode = "fast"

    message = EmailNotifier(EmailSettings(enabled=True, to_addrs=["enabled@example.com"])).build_message(alert)
    body = message.get_content()

    assert message["To"] == "enabled@example.com"
    assert "Short summary: This is an AI News Monitor test notification." in body
    assert "Market-watch suggestions:" in body
    assert "TEST: unclear, low, Test notifications are not real market events." in body
    assert "Recommended user action: watch only" in body


def test_email_send_uses_enabled_recipient_and_alert_body(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            assert username == "sender@example.com"
            assert password == "app-password"

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setenv("EMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setenv("EMAIL_FROM", "sender@example.com")
    monkeypatch.setattr("src.notifiers.email_notifier.smtplib.SMTP", FakeSMTP)
    alert = sample_alert()
    alert.mode = "fast"

    result = EmailNotifier(EmailSettings(enabled=True, to_addrs=["enabled@example.com"])).send(alert)

    assert result.success
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "enabled@example.com"
    body = sent_messages[0].get_content()
    assert "Short summary: This is an AI News Monitor test notification." in body
    assert "Market-watch suggestions:" in body
    assert "Recommended user action: watch only" in body


def test_enabled_email_settings_create_email_notifier():
    notifiers = build_notifiers(NotifierSettings(email=EmailSettings(enabled=True, to_addrs=["enabled@example.com"])))

    assert [notifier.name for notifier in notifiers] == ["Email"]


def test_generic_webhook_default_payload():
    alert = sample_alert()
    notifier = GenericWebhookNotifier(GenericWebhookSettings(enabled=True))
    payload = notifier.build_payload(alert)
    assert payload["title"] == alert.title
    assert payload["links"] == [alert.article.url]


def test_alert_text_contains_required_sections():
    text = format_alert_text(sample_alert())
    for section in [
        "Topic:",
        "Relevance score:",
        "Original links:",
        "Market-watch suggestions:",
        "Recommended user action:",
        "Bullish scenario:",
        "Bearish scenario:",
        "Risk notes:",
        "Uncertainty notes:",
    ]:
        assert section in text
