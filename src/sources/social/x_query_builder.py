from __future__ import annotations

from src.models import TopicConfig, XSourceSettings

SPAM_EXCLUSIONS = ["giveaway", "airdrop", "pump", "moon", "casino"]


def build_x_recent_search_queries(topic: TopicConfig, settings: XSourceSettings) -> list[str]:
    terms = _topic_terms(topic)
    if not terms:
        terms = [topic.name]
    queries: list[str] = []
    account_filter = " OR ".join(f"from:{account.lstrip('@')}" for account in settings.trusted_accounts)
    exclusions = " ".join(f"-{term}" for term in SPAM_EXCLUSIONS)
    retweet_filter = "" if settings.include_retweets else " -is:retweet"
    for term in terms[:3]:
        query = f'("{term}") {exclusions}{retweet_filter}'.strip()
        queries.append(query)
    if account_filter:
        queries.append(f"({account_filter}) ({' OR '.join(terms[:4])}){retweet_filter}".strip())
    return [_truncate_query(query) for query in dict.fromkeys(queries)]


def _topic_terms(topic: TopicConfig) -> list[str]:
    raw_terms = [topic.name, *topic.keywords]
    terms: list[str] = []
    for term in raw_terms:
        cleaned = " ".join(str(term).replace('"', " ").split())
        if len(cleaned) >= 3:
            terms.append(cleaned)
    return terms


def _truncate_query(query: str, limit: int = 512) -> str:
    if len(query) <= limit:
        return query
    return query[:limit].rsplit(" ", 1)[0]
