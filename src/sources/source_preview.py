from __future__ import annotations

from src.i18n import text
from src.models import AppConfig, TopicConfig
from src.sources.source_discovery import discover_sources_for_topic


def topic_source_preview_lines(topic: TopicConfig, config: AppConfig, language: str | None = None) -> list[str]:
    lines: list[str] = [
        text("source_preview_mode", language, mode=topic.source_mode),
        text("source_preview_domains", language, domains=", ".join(topic.domains) or "-"),
    ]
    manual_sources = _manual_source_preview_names(config)
    if topic.source_mode in {"manual", "hybrid"}:
        lines.append(text("source_preview_manual_header", language))
        if manual_sources:
            lines.extend(f"- {name}" for name in manual_sources)
        else:
            lines.append(f"- {text('source_preview_no_manual_sources', language)}")
    if topic.source_mode in {"auto", "hybrid"}:
        selected = discover_sources_for_topic(topic, config.sources)
        lines.append(text("source_preview_auto_header", language))
        if not selected:
            lines.append(f"- {text('source_preview_no_auto_sources', language)}")
        for item in selected:
            risk = item.risk or text("alert.none", language)
            lines.append(
                "- "
                + text(
                    "source_preview_auto_line",
                    language,
                    name=item.candidate.name,
                    source_type=item.candidate.source_type,
                    reason=item.reason,
                    expected=item.expected_value,
                    risk=risk,
                    priority=item.priority,
                )
            )
    if topic.social_enabled and topic.source_mode in {"auto", "hybrid"}:
        state = text("enabled", language) if config.social_sources.x.enabled else text("disabled", language)
        lines.append(text("source_preview_x_state", language, state=state))
    return lines


def _manual_source_preview_names(config: AppConfig) -> list[str]:
    names: list[str] = []
    if config.sources.gdelt.enabled:
        names.append("GDELT Free News API")
    if config.sources.google_news_rss.enabled:
        names.append("Google News RSS")
    if config.sources.yahoo_finance_rss.enabled:
        names.append("Yahoo Finance RSS")
    names.extend(f"Public RSS: {url}" for url in config.sources.public_rss.urls if config.sources.public_rss.enabled)
    names.extend(
        f"Official RSS: {url}" for url in config.sources.official_rss.urls if config.sources.official_rss.enabled
    )
    names.extend(source.name for source in config.sources.library if source.enabled)
    names.extend(source.name for source in config.sources.custom_sources if source.enabled)
    return names
