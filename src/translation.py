from __future__ import annotations

import logging
from typing import Protocol

from src.language import detect_supported_language, normalize_language
from src.models import Article

logger = logging.getLogger(__name__)


class TranslationClient(Protocol):
    api_key: str | None

    def translate_and_summarize(self, article: Article, target_language: str) -> dict[str, str]: ...


def enrich_article_language(
    article: Article,
    *,
    target_language: str,
    translation_enabled: bool,
    summary_enabled: bool,
    llm_client: TranslationClient | None = None,
) -> Article:
    article.language = detect_supported_language(article.title, article.snippet, fallback=article.language)
    normalized_target = normalize_language(target_language) or "zh-CN"
    article.short_summary = article.short_summary or _fallback_summary(article)
    if not summary_enabled:
        article.short_summary = None
    if not translation_enabled or article.language == normalized_target:
        return article
    if not llm_client or not getattr(llm_client, "api_key", None):
        logger.info("Translation skipped because LLM API key is not configured.")
        return article
    try:
        payload = llm_client.translate_and_summarize(article, normalized_target)
    except Exception as exc:  # noqa: BLE001 - translation must not block monitoring
        logger.warning("Translation failed for %s: %s", article.url, exc)
        return article
    article.translated_title = payload.get("translated_title") or article.translated_title
    article.translated_snippet = payload.get("translated_snippet") or article.translated_snippet
    if summary_enabled:
        article.short_summary = payload.get("summary") or article.short_summary
    return article


def _fallback_summary(article: Article) -> str:
    text = article.snippet or article.title
    return text[:280]
