from __future__ import annotations

from typing import Any

import httpx

from src.models import SocialPostItem, TopicConfig, XSourceSettings
from src.secrets import get_env_secret
from src.sources.social.x_normalizer import normalize_x_post
from src.sources.social.x_query_builder import build_x_recent_search_queries
from src.utils.http_utils import request_with_retries


class XClient:
    base_url = "https://api.x.com/2"

    def __init__(self, settings: XSourceSettings, client: httpx.Client | None = None, bearer_token: str | None = None):
        self.settings = settings
        self.client = client
        self.bearer_token = bearer_token if bearer_token is not None else get_env_secret(settings.bearer_token_env)

    def enabled_and_configured(self) -> bool:
        return self.settings.enabled and bool(self.bearer_token)

    def validate_ready(self) -> None:
        if not self.settings.enabled:
            raise ValueError("X.com source is disabled.")
        if not self.bearer_token:
            raise ValueError(f"X.com bearer token is missing from {self.settings.bearer_token_env}.")

    def recent_search(self, topic: TopicConfig, max_results: int | None = None) -> list[SocialPostItem]:
        self.validate_ready()
        requested_limit = self.settings.max_posts_per_topic_per_run if max_results is None else max_results
        post_limit = max(0, min(requested_limit, self.settings.max_posts_per_topic_per_run))
        if post_limit <= 0:
            return []
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=20)
        posts: list[SocialPostItem] = []
        try:
            for query in build_x_recent_search_queries(topic, self.settings):
                remaining = post_limit - len(posts)
                if remaining <= 0:
                    break
                payload = self._search_query(client, query, max_results=remaining)
                posts.extend(normalize_x_post(item) for item in _post_payloads_with_authors(payload))
                if len(posts) >= post_limit:
                    return posts[:post_limit]
            return posts[:post_limit]
        finally:
            if close_client:
                client.close()

    def _search_query(self, client: httpx.Client, query: str, *, max_results: int) -> dict[str, Any]:
        response = request_with_retries(
            client,
            "GET",
            f"{self.base_url}/tweets/search/recent",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            params={
                "query": query,
                "max_results": max(1, min(100, max_results)),
                "tweet.fields": "author_id,created_at,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "username,public_metrics",
            },
        )
        return response.json()


def _post_payloads_with_authors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    users = {
        str(user.get("id") or ""): user
        for user in (payload.get("includes") or {}).get("users") or []
        if isinstance(user, dict)
    }
    enriched: list[dict[str, Any]] = []
    for item in payload.get("data", []) or []:
        if not isinstance(item, dict):
            continue
        user = users.get(str(item.get("author_id") or ""))
        if user:
            metrics = user.get("public_metrics") or {}
            item = {
                **item,
                "author_username": user.get("username"),
                "author_followers_count": metrics.get("followers_count"),
            }
        enriched.append(item)
    return enriched
