from __future__ import annotations

from src.models import Article, SocialPostItem, TopicConfig, XSourceSettings
from src.sources.base import NewsSource
from src.sources.social.x_client import XClient
from src.utils.time_utils import utc_now


class XRecentSearchSource(NewsSource):
    name = "X.com Recent Search"

    def __init__(self, settings: XSourceSettings, client: XClient | None = None):
        self.settings = settings
        self.client = client or XClient(settings)
        self._daily_read_date: str | None = None
        self._daily_read_posts = 0
        self.last_cost_guard_warning: str | None = None

    def fetch(self, topic: TopicConfig) -> list[Article]:
        if not self._should_fetch(topic):
            return []
        max_results = self._cost_guard_limit()
        if max_results <= 0:
            self.last_cost_guard_warning = "X.com daily read-post budget exhausted; skipping recent search."
            return []
        posts = self.client.recent_search(topic, max_results=max_results)
        self._record_posts_read(len(posts))
        return [self._article_from_post(post) for post in posts if self._post_allowed(post)]

    def _should_fetch(self, topic: TopicConfig) -> bool:
        return self.settings.enabled and topic.social_enabled and topic.source_mode in {"auto", "hybrid"}

    def _post_allowed(self, post: SocialPostItem) -> bool:
        username = (post.author_username or "").casefold()
        blocked = {account.lstrip("@").casefold() for account in self.settings.blocked_accounts}
        trusted = {account.lstrip("@").casefold() for account in self.settings.trusted_accounts}
        if username and username in blocked:
            return False
        if trusted and username not in trusted:
            return False
        follower_count = post.metrics.get("author_followers_count")
        if self.settings.min_author_followers is not None:
            try:
                if int(follower_count or 0) < self.settings.min_author_followers:
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def _cost_guard_limit(self) -> int:
        if not self.settings.cost_guard.enabled:
            return self.settings.max_posts_per_topic_per_run
        self._reset_cost_guard_if_needed()
        remaining = self.settings.cost_guard.daily_max_read_posts - self._daily_read_posts
        return max(0, min(self.settings.max_posts_per_topic_per_run, remaining))

    def _record_posts_read(self, count: int) -> None:
        if not self.settings.cost_guard.enabled:
            return
        self._reset_cost_guard_if_needed()
        self._daily_read_posts += max(0, count)
        limit = self.settings.cost_guard.daily_max_read_posts
        percent = int((self._daily_read_posts / limit) * 100) if limit else 100
        if percent >= self.settings.cost_guard.warn_when_reaching_percent:
            self.last_cost_guard_warning = (
                f"X.com recent-search read usage is at {percent}% of the configured daily guard."
            )

    def _reset_cost_guard_if_needed(self) -> None:
        today = utc_now().date().isoformat()
        if self._daily_read_date != today:
            self._daily_read_date = today
            self._daily_read_posts = 0
            self.last_cost_guard_warning = None

    def _article_from_post(self, post: SocialPostItem) -> Article:
        title = _social_title(post)
        return Article(
            title=title,
            url=post.url,
            source=self.name,
            published_at=post.created_at,
            snippet=post.text,
            language=None,
            raw={
                "platform": post.platform,
                "post_id": post.post_id,
                "author_id": post.author_id,
                "author_username": post.author_username,
                "metrics": post.metrics,
                "referenced_urls": post.referenced_urls,
            },
            reliability_score=post.source_confidence_hint,
            category="Social",
            source_type="x",
            source_url=post.url,
            source_tier=4,
            source_role="custom",
            editorial_context="X.com recent-search signal. Treat as unconfirmed unless corroborated.",
            confirmation_source_count=1,
            independent_source_count=1,
        )


def _social_title(post: SocialPostItem) -> str:
    author = f"@{post.author_username}: " if post.author_username else "X.com post: "
    text = " ".join(post.text.split())
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    return f"{author}{text}" if text else f"{author}{post.post_id}"
