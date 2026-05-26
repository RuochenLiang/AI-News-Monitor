from __future__ import annotations

from datetime import UTC, datetime

from src.dedupe import dedupe_articles
from src.llm_client import parse_llm_analysis
from src.models import Alert, Article
from src.storage import SQLiteStore
from src.utils.url_utils import normalize_url
from tests.test_llm_schema import VALID_JSON


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


def test_sqlite_recent_alert_similarity_dedupe(tmp_path):
    store = SQLiteStore(tmp_path / "monitor.sqlite")
    article = Article(
        "NVIDIA H20 China export license review",
        "https://example.com/h20-license",
        "Source",
        datetime.now(UTC),
    )
    payload = dict(
        VALID_JSON,
        event_title="NVIDIA H20 China export license review",
        notification_title="NVIDIA H20 China export license review",
        summary="NVIDIA H20 China export license review affects chip shipment paperwork.",
        event_summary="NVIDIA H20 China export license review affects chip shipment paperwork.",
    )
    alert = Alert("topic", article, parse_llm_analysis(payload), datetime.now(UTC))
    store.save_alert(alert)

    assert store.seen_similar_alert_recently(
        "topic",
        "Industry memo says NVIDIA H20 China export license review changes shipment paperwork.",
        72,
    )
    assert not store.seen_similar_alert_recently("topic", "Taiwan election polling location update", 72)
