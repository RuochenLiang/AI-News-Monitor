from __future__ import annotations

from abc import ABC, abstractmethod

from src.i18n import text
from src.models import Alert, NotificationResult

DISCLAIMER = text("disclaimer", "en")


class Notifier(ABC):
    name: str

    @abstractmethod
    def send(self, alert: Alert) -> NotificationResult:
        raise NotImplementedError

    def health_check(self) -> NotificationResult:
        return NotificationResult(self.name, True)


def format_alert_text(alert: Alert, language: str | None = None, mode: str | None = None) -> str:
    analysis = alert.analysis
    article = alert.article
    language = language or alert.output_language
    mode = mode or alert.mode
    if mode == "fast":
        return _format_fast_alert(alert, language)
    suggestions = _format_market_watch_suggestions(alert, language)
    published = article.published_at.isoformat() if article.published_at else text("alert.not_available", language)
    return (
        f"{alert.title}\n\n"
        f"{text('alert.topic', language)}: {alert.topic_name}\n"
        f"{text('alert.relevance_score', language)}: {analysis.relevance_score}\n"
        f"{text('alert.article_title', language)}: {article.title}\n"
        f"{text('alert.source', language)}: {article.source}\n"
        f"{text('alert.published_time', language)}: {published}\n"
        f"{text('alert.original_links', language)}:\n- {article.url}\n\n"
        f"{text('alert.summary', language)}:\n{analysis.summary}\n\n"
        f"{text('alert.why_it_matters', language)}:\n{analysis.why_it_matters}\n\n"
        f"{text('alert.market_watch', language)}:\n{suggestions}\n\n"
        f"{text('alert.recommended_user_action', language)}: {_format_user_action(analysis.recommended_user_action)}\n\n"
        f"{text('alert.bullish', language)}:\n{analysis.bullish_path}\n\n"
        f"{text('alert.bearish', language)}:\n{analysis.bearish_path}\n\n"
        f"{text('alert.risk_notes', language)}:\n{analysis.risk_notes}\n\n"
        f"{text('alert.uncertainty_notes', language)}:\n{analysis.uncertainty_notes}\n\n"
        f"{text('disclaimer', language)}"
    )


def format_test_alert_text(channel_name: str, language: str | None = None) -> str:
    language = language or "en"
    return f"{text('test_notification_body', language, channel_name=channel_name)}\n\n{text('disclaimer', language)}"


def _format_fast_alert(alert: Alert, language: str | None = None) -> str:
    analysis = alert.analysis
    article = alert.article
    published = article.published_at.isoformat() if article.published_at else text("alert.not_available", language)
    translated_title = article.translated_title or ""
    summary = article.short_summary or analysis.summary
    suggestions = _format_market_watch_suggestions(alert, language)
    keywords = (
        ", ".join(article.matched_keywords) if article.matched_keywords else text("alert.not_available", language)
    )
    context_bits = [
        f"reliability {article.reliability_score:.2f}",
        f"Tier {article.source_tier}",
        article.source_role.replace("_", " "),
        article.category or "",
        article.ownership or "",
        f"propaganda risk {article.propaganda_risk}" if article.propaganda_risk != "unknown" else "",
        article.editorial_context or "",
        article.bias_hint or "",
    ]
    context = "; ".join(bit for bit in context_bits if bit)
    cluster = article.event_cluster_id or text("alert.not_available", language)
    reason = article.selection_reason or article.match_reason or text("alert.default_reason", language)
    translated_line = (
        f"{text('alert.translated_title', language)}: {translated_title}\n"
        if translated_title and translated_title != article.title
        else ""
    )
    return (
        f"{alert.title}\n\n"
        f"{text('alert.topic', language)}: {alert.topic_name}\n"
        f"{text('alert.mode', language)}: Fast Alert\n"
        f"{text('alert.relevance_score', language)}: {analysis.relevance_score}\n"
        f"{text('alert.article_title', language)}: {article.title}\n"
        f"{translated_line}"
        f"{text('alert.source', language)}: {article.source}\n"
        f"{text('alert.published_time', language)}: {published}\n"
        f"{text('alert.original_url', language)}: {article.url}\n"
        f"{text('alert.short_summary', language)}: {summary}\n"
        f"{text('alert.market_watch', language)}:\n{suggestions}\n"
        f"{text('alert.recommended_user_action', language)}: {_format_user_action(analysis.recommended_user_action)}\n"
        f"{text('alert.match_reason', language)}: {article.match_reason or reason}\n"
        f"{text('alert.keywords', language)}: {keywords}\n"
        f"{text('alert.source_context', language)}: {context or text('alert.not_available', language)}\n"
        f"{text('alert.cluster', language)}: {cluster}\n"
        f"{text('alert.confirmation', language)}: {article.confirmation_summary or text('alert.not_available', language)}\n"
        f"{text('alert.why_selected', language)}: {reason}\n\n"
        f"{text('disclaimer', language)}"
    )


def _format_market_watch_suggestions(alert: Alert, language: str | None = None) -> str:
    return (
        "\n".join(
            f"- {item.ticker or item.name_or_theme}: {item.possible_direction}, {item.confidence}, {item.reason}"
            for item in alert.analysis.market_watch_suggestions
        )
        or f"- {text('alert.none', language)}"
    )


def _format_user_action(action: str) -> str:
    return action.replace("_", " ")
