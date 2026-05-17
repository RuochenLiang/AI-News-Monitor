from __future__ import annotations

from src.models import EmailSettings, GenericWebhookSettings
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
        "Bullish scenario:",
        "Bearish scenario:",
        "Risk notes:",
        "Uncertainty notes:",
    ]:
        assert section in text
