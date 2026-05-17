from __future__ import annotations

from datetime import UTC, datetime

from src.dedupe import dedupe_articles
from src.models import Article
from src.storage import SQLiteStore
from src.utils.url_utils import normalize_url


def test_url_normalization_removes_tracking_params():
    url = "HTTPS://www.Example.com/news/?utm_source=x&b=2&a=1#section"
    assert normalize_url(url) == "https://example.com/news?a=1&b=2"


def test_in_memory_article_deduplication():
    articles = [
        Article("Same title", "https://example.com/a?utm_campaign=x", "A"),
        Article("Same title", "https://example.com/a", "B"),
        Article("Different", "https://example.com/b", "A"),
    ]
    assert len(dedupe_articles(articles)) == 2


def test_sqlite_processed_and_title_hash_dedupe(tmp_path):
    store = SQLiteStore(tmp_path / "monitor.sqlite")
    article = Article("Important News", "https://example.com/news", "Source", datetime.now(UTC))
    assert not store.is_processed(article, "topic")
    assert not store.seen_similar_recently(article, "topic", 72)
    store.upsert_article(article, "topic")
    store.mark_processed(article, "topic")
    assert store.is_processed(article, "topic")
    similar = Article("Important News", "https://another.example/news", "Source", datetime.now(UTC))
    assert store.seen_similar_recently(similar, "topic", 72)
