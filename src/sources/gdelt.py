from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

import httpx

from src.models import Article, TopicConfig
from src.sources.base import NewsSource
from src.utils.http_utils import request_with_retries
from src.utils.text_utils import clean_text
from src.utils.time_utils import parse_datetime

logger = logging.getLogger(__name__)

_GDELT_SHORT_TOKEN_EXPANSIONS = {
    "AI": "artificial intelligence",
    "US": "United States",
    "U.S": "United States",
    "U.S.": "United States",
    "UK": "United Kingdom",
    "EU": "European Union",
}
_GDELT_FRAGMENT_STOPWORDS = {"a", "an", "and", "or", "not", "the", "of", "for", "to", "in", "on", "with"}
_GDELT_TERM_MAX_LENGTH = 120


class GdeltSource(NewsSource):
    name = "GDELT"
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"
    max_query_length = 900

    def __init__(self, timeout_seconds: int = 20, client: httpx.Client | None = None, max_records: int = 20):
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.max_records = max_records

    def fetch(self, topic: TopicConfig) -> list[Article]:
        params = gdelt_params_for_topic(topic, max_records=self.max_records)
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=True)
        try:
            response = request_with_retries(client, "GET", self.endpoint, params=params)
            payload = parse_gdelt_json_response(response)
        finally:
            if close_client:
                client.close()
        articles = [self._article_from_item(item) for item in payload.get("articles", []) or []]
        result = [article for article in articles if article]
        logger.info("%s fetched %s articles for topic %s", self.name, len(result), topic.name)
        return result

    def _article_from_item(self, item: dict) -> Article | None:
        title = clean_text(item.get("title"))
        url = str(item.get("url") or "").strip()
        if not title or not url:
            return None
        return Article(
            title=title,
            url=url,
            source=self.name,
            published_at=parse_datetime(item.get("seendate") or item.get("date")),
            snippet=clean_text(item.get("seendesc") or item.get("description"), max_length=800) or None,
            language=str(item.get("language") or "").strip() or None,
            raw=item,
            reliability_score=0.7,
            ownership="GDELT aggregated public web coverage",
            bias_hint="aggregator; verify original publisher context",
            category="Global News",
            source_type="api",
            source_url=self.endpoint,
            source_tier=4,
            source_role="aggregator",
            propaganda_risk="unknown",
            editorial_context="Public web index aggregator; verify original publisher context.",
        )


def build_gdelt_query(topic: TopicConfig, *, keyword_limit: int = 8) -> str:
    keywords = _sanitized_keyword_list(topic.keywords, keyword_limit=keyword_limit)
    if not keywords:
        fallback = sanitize_gdelt_keyword(topic.name)
        keywords = [fallback] if fallback else []
    if not keywords:
        raise ValueError("unsupported_query_shape: empty GDELT query")
    while keywords:
        terms = [f'"{keyword}"' for keyword in keywords]
        query = f"({' OR '.join(terms)})" if len(terms) > 1 else terms[0]
        try:
            validate_gdelt_query(query)
            return query
        except ValueError as exc:
            if len(keywords) > 1 and str(exc).startswith(("query_too_long:", "invalid_encoded_query:")):
                keywords.pop()
                continue
            raise
    raise ValueError("unsupported_query_shape: empty GDELT query")


def sanitize_gdelt_keyword(keyword: object) -> str | None:
    text = " ".join(str(keyword or "").split())
    if not text:
        return None
    text = text.translate(str.maketrans({"“": "", "”": "", "‘": "", "’": "", "`": "", "´": "", '"': "", "'": ""}))
    text = re.sub(r"[|{}<>\\]", " ", text)
    text = re.sub(r"\s+[,;:]+\s+", " ", text)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n,.;:-_/()[]")
    if not text:
        return None
    normalized = re.sub(r"\s+", " ", text)
    expansion_key = normalized.upper()
    if expansion_key in _GDELT_SHORT_TOKEN_EXPANSIONS:
        return _GDELT_SHORT_TOKEN_EXPANSIONS[expansion_key]
    tokens = re.findall(r"[A-Za-z0-9]+", normalized)
    if not tokens or all(token.casefold() in _GDELT_FRAGMENT_STOPWORDS for token in tokens):
        return None
    alnum = "".join(tokens)
    if len(alnum) < 3:
        return None
    if len(normalized) > _GDELT_TERM_MAX_LENGTH:
        normalized = (
            normalized[:_GDELT_TERM_MAX_LENGTH].rsplit(" ", 1)[0].strip() or normalized[:_GDELT_TERM_MAX_LENGTH]
        )
    return normalized


def gdelt_params_for_topic(topic: TopicConfig, *, max_records: int = 20) -> dict[str, str]:
    return {
        "query": build_gdelt_query(topic),
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "HybridRel",
    }


def validate_gdelt_query(query: str) -> None:
    if not query.strip():
        raise ValueError("unsupported_query_shape: empty GDELT query")
    if len(query) > GdeltSource.max_query_length:
        raise ValueError("query_too_long: reduce keywords or OR terms")
    encoded = quote_plus(query)
    if "%" in query or len(encoded) > GdeltSource.max_query_length * 3:
        raise ValueError("invalid_encoded_query: query appears malformed after URL encoding")
    if query.count('"') % 2:
        raise ValueError("unsupported_query_shape: unbalanced quote in GDELT query")
    quoted_phrases = re.findall(r'"([^"]*)"', query)
    for phrase in quoted_phrases:
        if len(re.sub(r"[^A-Za-z0-9]", "", phrase)) < 3:
            raise ValueError("unsupported_query_shape: quoted phrase is too short")
    if not quoted_phrases:
        tokens = re.findall(r"[A-Za-z0-9]+", query)
        if tokens and all(len(token) < 3 for token in tokens):
            raise ValueError("unsupported_query_shape: query phrase is too short")


def _sanitized_keyword_list(keywords: list[str], *, keyword_limit: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        sanitized = sanitize_gdelt_keyword(keyword)
        if not sanitized:
            continue
        key = sanitized.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(sanitized)
        if len(output) >= keyword_limit:
            break
    return output


def parse_gdelt_json_response(response: httpx.Response) -> dict:
    content_type = response.headers.get("content-type", "").casefold()
    preview = response.text[:300].strip().replace("\n", " ")
    if "json" not in content_type and response.text.strip() and not response.text.lstrip().startswith(("{", "[")):
        raise ValueError(f"api_bad_response: GDELT returned non-JSON response preview: {preview}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"feed_parse_failed: GDELT JSON parse failed. Response preview: {preview}") from exc
    if not isinstance(payload, dict):
        raise ValueError("api_bad_response: GDELT JSON response was not an object")
    return payload
