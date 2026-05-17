from __future__ import annotations

from src.models import Article
from src.utils.text_utils import title_hash
from src.utils.url_utils import normalize_url


def article_identity(article: Article) -> tuple[str, str, str]:
    published_day = article.published_at.date().isoformat() if article.published_at else ""
    return (normalize_url(article.url), title_hash(article.title), f"{article.source}:{article.title}:{published_day}")


def dedupe_articles(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    result: list[Article] = []
    for article in articles:
        identities = article_identity(article)
        if any(identity in seen for identity in identities if identity):
            continue
        seen.update(identity for identity in identities if identity)
        result.append(article)
    return result
