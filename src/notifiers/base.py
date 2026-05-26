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
    if _has_event_synthesis(alert):
        return _format_event_alert(alert, language)
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


def _format_event_alert(alert: Alert, language: str | None = None) -> str:
    analysis = alert.analysis
    article_count = analysis.grouped_article_count
    timeline = _format_timeline(alert, language)
    sources = _format_sources(alert, language)
    key_facts = _format_list(analysis.key_facts, language)
    uncertainty = _format_list(analysis.uncertainties, language)
    suggested = _format_list(analysis.suggested_actions, language)
    grouped_line = (
        f"{text('alert.grouped_articles', language)}: {article_count}\n" if int(article_count or 0) > 1 else ""
    )
    current_status = analysis.current_status or text("alert.not_available", language)
    summary = analysis.event_summary or analysis.summary
    relation_reason = analysis.relation_reason or text("alert.not_available", language)
    return (
        f"{alert.title}\n\n"
        f"{text('alert.topic', language)}: {alert.topic_name}\n"
        f"{grouped_line}"
        f"{text('alert.current_status', language)}:\n{current_status}\n\n"
        f"{text('alert.summary', language)}:\n{summary}\n\n"
        f"{text('alert.key_facts', language)}:\n{key_facts}\n\n"
        f"{text('alert.timeline', language)}:\n{timeline}\n\n"
        f"{text('alert.why_it_matters', language)}:\n{analysis.why_it_matters}\n\n"
        f"{text('alert.sources', language)}:\n{sources}\n\n"
        f"{text('alert.relation_reason', language)}:\n{relation_reason}\n\n"
        f"{text('alert.uncertainty', language)}:\n{uncertainty}\n\n"
        f"{text('alert.suggested_follow_up', language)}:\n{suggested}\n\n"
        f"{text('disclaimer', language)}"
    )


def _has_event_synthesis(alert: Alert) -> bool:
    analysis = alert.analysis
    return bool(
        alert.event_cluster
        or analysis.event_title
        or analysis.event_summary
        or analysis.timeline
        or analysis.source_links
        or int(analysis.grouped_article_count or 1) > 1
    )


def _format_timeline(alert: Alert, language: str | None = None) -> str:
    items = alert.analysis.timeline or (alert.event_cluster.timeline if alert.event_cluster else [])
    if not items:
        return f"- {text('alert.not_available', language)}"
    lines = []
    for item in items[:8]:
        time = f" {item.time}" if item.time else ""
        source = f" ({item.source_title})" if item.source_title else ""
        lines.append(f"- {item.date}{time}: {item.description}{source}")
    return "\n".join(lines)


def _format_sources(alert: Alert, language: str | None = None) -> str:
    links = alert.analysis.source_links
    if not links and alert.event_cluster:
        from src.event_synthesis import source_links_from_articles

        links = source_links_from_articles(alert.event_cluster.articles)
    if not links:
        return f"1. {alert.article.source} — {alert.article.title}\n   {alert.article.url}"
    return "\n".join(
        f"{index}. {link.publisher or text('alert.source', language)} — {link.title}\n   {link.url}"
        for index, link in enumerate(links, start=1)
    )


def _format_list(items: list[str], language: str | None = None) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return f"- {text('alert.none', language)}"
    return "\n".join(f"- {item}" for item in cleaned[:8])


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
