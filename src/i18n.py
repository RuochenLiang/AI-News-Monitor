from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "zh-CN"}


def normalize_ui_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def text(key: str, language: str | None = None, **kwargs: Any) -> str:
    language = normalize_ui_language(language)
    value = _catalog(language).get(key) or _catalog(DEFAULT_LANGUAGE).get(key) or key
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def catalog(language: str | None = None) -> dict[str, str]:
    return dict(_catalog(normalize_ui_language(language)))


@cache
def _catalog(language: str) -> dict[str, str]:
    path = _locales_dir() / f"{language}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in payload.items()}


def _locales_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "locales"
