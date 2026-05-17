from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.models import Alert, Article
from src.utils.text_utils import title_hash
from src.utils.time_utils import iso_or_empty, parse_datetime, utc_now
from src.utils.url_utils import normalize_url


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS articles(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT,
                  normalized_url TEXT,
                  title TEXT,
                  title_hash TEXT,
                  source TEXT,
                  published_at TEXT,
                  first_seen_at TEXT,
                  last_seen_at TEXT,
                  topic_name TEXT,
                  processed INTEGER DEFAULT 0,
                  UNIQUE(normalized_url, topic_name)
                );

                CREATE TABLE IF NOT EXISTS alerts(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_name TEXT,
                  article_url TEXT,
                  title TEXT,
                  relevance_score INTEGER,
                  summary TEXT,
                  llm_json TEXT,
                  sent_at TEXT
                );

                CREATE TABLE IF NOT EXISTS notification_results(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  alert_id INTEGER,
                  notifier_name TEXT,
                  success INTEGER,
                  error_message TEXT,
                  sent_at TEXT
                );

                CREATE TABLE IF NOT EXISTS source_states(
                  source_name TEXT PRIMARY KEY,
                  state_json TEXT,
                  updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS source_cache(
                  cache_key TEXT PRIMARY KEY,
                  source_name TEXT,
                  topic_name TEXT,
                  articles_json TEXT,
                  cached_at TEXT,
                  last_known_good_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_articles_topic_processed
                  ON articles(topic_name, processed);
                CREATE INDEX IF NOT EXISTS idx_articles_title_hash
                  ON articles(topic_name, title_hash);
                CREATE INDEX IF NOT EXISTS idx_alerts_topic_sent
                  ON alerts(topic_name, sent_at);
                CREATE INDEX IF NOT EXISTS idx_source_cache_source_topic
                  ON source_cache(source_name, topic_name);
                """)

    def upsert_article(self, article: Article, topic_name: str) -> int:
        now = utc_now().isoformat()
        normalized = normalize_url(article.url)
        hash_value = title_hash(article.title)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO articles(
                    url, normalized_url, title, title_hash, source, published_at,
                    first_seen_at, last_seen_at, topic_name, processed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(normalized_url, topic_name) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    title=excluded.title,
                    source=excluded.source,
                    published_at=excluded.published_at
                """,
                (
                    article.url,
                    normalized,
                    article.title,
                    hash_value,
                    article.source,
                    iso_or_empty(article.published_at),
                    now,
                    now,
                    topic_name,
                ),
            )
            row = conn.execute(
                "SELECT id FROM articles WHERE normalized_url=? AND topic_name=?",
                (normalized, topic_name),
            ).fetchone()
            return int(row["id"])

    def is_processed(self, article: Article, topic_name: str) -> bool:
        normalized = normalize_url(article.url)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT processed FROM articles WHERE normalized_url=? AND topic_name=?",
                (normalized, topic_name),
            ).fetchone()
        return bool(row and row["processed"])

    def mark_processed(self, article: Article, topic_name: str) -> None:
        normalized = normalize_url(article.url)
        with self.connect() as conn:
            conn.execute(
                "UPDATE articles SET processed=1, last_seen_at=? WHERE normalized_url=? AND topic_name=?",
                (utc_now().isoformat(), normalized, topic_name),
            )

    def seen_similar_recently(self, article: Article, topic_name: str, dedupe_hours: int) -> bool:
        cutoff = utc_now() - timedelta(hours=dedupe_hours)
        normalized = normalize_url(article.url)
        hash_value = title_hash(article.title)
        published_day = article.published_at.date().isoformat() if article.published_at else ""
        with self.connect() as conn:
            url_row = conn.execute(
                """
                SELECT id, first_seen_at FROM articles
                WHERE normalized_url=? AND topic_name=?
                """,
                (normalized, topic_name),
            ).fetchone()
            if url_row and _after_cutoff(url_row["first_seen_at"], cutoff):
                return True

            title_row = conn.execute(
                """
                SELECT id, first_seen_at FROM articles
                WHERE title_hash=? AND topic_name=?
                ORDER BY first_seen_at DESC LIMIT 1
                """,
                (hash_value, topic_name),
            ).fetchone()
            if title_row and _after_cutoff(title_row["first_seen_at"], cutoff):
                return True

            if published_day:
                fallback = conn.execute(
                    """
                    SELECT id, first_seen_at FROM articles
                    WHERE source=? AND title=? AND substr(published_at, 1, 10)=? AND topic_name=?
                    ORDER BY first_seen_at DESC LIMIT 1
                    """,
                    (article.source, article.title, published_day, topic_name),
                ).fetchone()
                if fallback and _after_cutoff(fallback["first_seen_at"], cutoff):
                    return True
        return False

    def save_alert(self, alert: Alert) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO alerts(topic_name, article_url, title, relevance_score, summary, llm_json, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.topic_name,
                    alert.article.url,
                    alert.title,
                    alert.analysis.relevance_score,
                    alert.analysis.summary,
                    json.dumps(alert.analysis.to_dict(), ensure_ascii=False),
                    alert.sent_at.isoformat(),
                ),
            )
            return int(cur.lastrowid)

    def record_notification(
        self, alert_id: int | None, notifier_name: str, success: bool, error_message: str | None
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO notification_results(alert_id, notifier_name, success, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (alert_id, notifier_name, 1 if success else 0, error_message, utc_now().isoformat()),
            )

    def latest_alert_for_topic(self, topic_name: str) -> datetime | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT sent_at FROM alerts WHERE topic_name=? ORDER BY sent_at DESC LIMIT 1",
                (topic_name,),
            ).fetchone()
        return parse_datetime(row["sent_at"]) if row else None

    def alert_count_since(self, since: datetime) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM alerts WHERE sent_at>=?", (since.isoformat(),)).fetchone()
        return int(row["count"] if row else 0)

    def alerts_sent_today(self) -> int:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.alert_count_since(today)

    def save_source_state(self, source_name: str, state: dict) -> None:
        payload = json.dumps(state, ensure_ascii=False, default=_json_default)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_states(source_name, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source_name) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (source_name, payload, utc_now().isoformat()),
            )

    def load_source_state(self, source_name: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM source_states WHERE source_name=?",
                (source_name,),
            ).fetchone()
        return json.loads(row["state_json"]) if row else None

    def load_all_source_states(self) -> dict[str, dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT source_name, state_json FROM source_states").fetchall()
        return {str(row["source_name"]): json.loads(row["state_json"]) for row in rows}

    def save_source_cache(self, cache_key: str, source_name: str, topic_name: str, articles: list[dict]) -> None:
        now = utc_now().isoformat()
        payload = json.dumps(articles, ensure_ascii=False, default=_json_default)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_cache(cache_key, source_name, topic_name, articles_json, cached_at, last_known_good_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    articles_json=excluded.articles_json,
                    cached_at=excluded.cached_at,
                    last_known_good_at=excluded.last_known_good_at
                """,
                (cache_key, source_name, topic_name, payload, now, now),
            )

    def load_source_cache(self, cache_key: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT source_name, topic_name, articles_json, cached_at, last_known_good_at
                FROM source_cache WHERE cache_key=?
                """,
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        return {
            "source_name": row["source_name"],
            "topic_name": row["topic_name"],
            "articles": json.loads(row["articles_json"] or "[]"),
            "cached_at": parse_datetime(row["cached_at"]),
            "last_known_good_at": parse_datetime(row["last_known_good_at"]),
        }

    def has_alert_for_article(self, article: Article, topic_name: str) -> bool:
        normalized = normalize_url(article.url)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM alerts
                WHERE topic_name=? AND article_url=?
                """,
                (topic_name, normalized),
            ).fetchone()
            exact = int(row["count"] if row else 0)
            if exact:
                return True
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM alerts
                WHERE topic_name=? AND article_url=?
                """,
                (topic_name, article.url),
            ).fetchone()
        return int(row["count"] if row else 0) > 0


def _after_cutoff(value: str | None, cutoff: datetime) -> bool:
    parsed = parse_datetime(value)
    return bool(parsed and parsed >= cutoff)


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
