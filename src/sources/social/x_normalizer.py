from __future__ import annotations

from datetime import datetime
from typing import Any

from src.models import SocialPostItem
from src.utils.time_utils import parse_datetime, utc_now


def normalize_x_post(payload: dict[str, Any]) -> SocialPostItem:
    post_id = str(payload.get("id") or "")
    author_id = str(payload.get("author_id") or "") or None
    username = _author_username(payload)
    created_at = _created_at(payload.get("created_at"))
    metrics = dict(payload.get("public_metrics") or {})
    if payload.get("author_followers_count") is not None:
        metrics["author_followers_count"] = payload["author_followers_count"]
    return SocialPostItem(
        platform="x",
        post_id=post_id,
        url=f"https://x.com/{username or 'i'}/status/{post_id}" if post_id else "",
        author_id=author_id,
        author_username=username,
        text=str(payload.get("text") or ""),
        created_at=created_at,
        metrics=metrics,
        referenced_urls=_referenced_urls(payload),
        source_confidence_hint=0.3,
    )


def _created_at(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if value:
        parsed = parse_datetime(str(value))
        if parsed:
            return parsed
    return utc_now()


def _author_username(payload: dict[str, Any]) -> str | None:
    username = payload.get("author_username")
    if username:
        return str(username).lstrip("@")
    includes = payload.get("includes") or {}
    users = includes.get("users") or []
    author_id = str(payload.get("author_id") or "")
    for user in users:
        if str(user.get("id") or "") == author_id and user.get("username"):
            return str(user["username"]).lstrip("@")
    return None


def _referenced_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in (payload.get("entities") or {}).get("urls") or []:
        expanded = item.get("expanded_url") or item.get("url")
        if expanded:
            urls.append(str(expanded))
    return urls
