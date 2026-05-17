from __future__ import annotations

import hashlib
import re
from html import unescape

WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: object, max_length: int | None = None) -> str:
    text = unescape(str(value or ""))
    text = TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 1].rstrip() + "..."
    return text


def title_hash(title: str) -> str:
    normalized = clean_text(title).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def keyword_matches(text: str, keywords: list[str]) -> bool:
    haystack = clean_text(text).casefold()
    return any(keyword.casefold() in haystack for keyword in keywords if keyword.strip())
