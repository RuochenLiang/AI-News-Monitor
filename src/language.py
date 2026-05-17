from __future__ import annotations

import re

SUPPORTED_LANGUAGES = {"zh-CN", "en"}


def normalize_language(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().replace("_", "-").casefold()
    if text in {"zh", "zh-cn", "zh-hans", "chinese", "mandarin", "cn"}:
        return "zh-CN"
    if text in {"en", "en-us", "en-gb", "english"}:
        return "en"
    return None


def detect_supported_language(*parts: str | None, fallback: str | None = None) -> str | None:
    normalized = normalize_language(fallback)
    if normalized:
        return normalized
    text = " ".join(part or "" for part in parts)
    if not text.strip():
        return None
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", text))
    if chinese_chars >= 2 and chinese_chars >= latin_words:
        return "zh-CN"
    if latin_words >= 2:
        return "en"
    if chinese_chars:
        return "zh-CN"
    return None


def is_supported_language(value: str | None) -> bool:
    return normalize_language(value) in SUPPORTED_LANGUAGES
