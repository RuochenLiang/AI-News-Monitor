from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from typing import Any

from src.models import AppConfig, Article, SourceHealthSettings
from src.sources.library import SOURCE_LIBRARY_CATEGORIES, SOURCE_PACKAGE_PRESETS
from src.utils.time_utils import parse_datetime, utc_now
from src.utils.url_utils import normalize_url

FRESHNESS_STATES = {"fresh", "stale", "very_stale", "no_data", "error", "disabled", "unknown"}
IMPORTANT_GROUPS = {
    "Official/Government",
    "Finance",
    "China/Taiwan",
    "Semiconductor/AI",
    "Company IR",
}


def compute_freshness_state(
    state: dict[str, Any] | None,
    settings: SourceHealthSettings | None = None,
    *,
    enabled: bool = True,
    now: datetime | None = None,
) -> str:
    settings = settings or SourceHealthSettings()
    now = now or utc_now()
    state = state or {}
    if not enabled:
        return "disabled"
    health = str(state.get("health") or "").casefold()
    if health == "error" or state.get("last_error_category") or state.get("last_failure_reason"):
        return "error"
    if int(state.get("articles") or state.get("last_article_count") or 0) == 0 and state.get("last_fetch_time"):
        return "no_data"
    last_success = parse_datetime(state.get("last_success_time"))
    if not last_success:
        return "unknown"
    age_minutes = max(0.0, (now - last_success).total_seconds() / 60)
    if age_minutes <= settings.fresh_within_minutes:
        return "fresh"
    if age_minutes >= settings.very_stale_after_minutes:
        return "very_stale"
    if age_minutes >= settings.stale_after_minutes:
        return "stale"
    return "stale"


def source_state_payload(
    *,
    source_name: str,
    metadata: dict[str, Any] | None,
    enabled: bool,
    health: str,
    articles: int = 0,
    last_fetch_time: datetime | None = None,
    last_success_time: datetime | None = None,
    last_failure_time: datetime | None = None,
    last_failure_reason: str | None = None,
    last_error_category: str | None = None,
    failure_count: int = 0,
    average_latency_ms: int | None = None,
    current_backoff_seconds: int = 0,
    next_retry_at: datetime | None = None,
    cache_status: str | None = None,
    cached_article_count: int = 0,
    settings: SourceHealthSettings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    payload = {
        "configured": True,
        "enabled": enabled,
        "source_name": source_name,
        "last_fetch_time": last_fetch_time,
        "last_success_time": last_success_time,
        "last_failure_time": last_failure_time,
        "last_failure_reason": last_failure_reason,
        "last_error_category": last_error_category,
        "failure_count": failure_count,
        "consecutive_failures": failure_count,
        "health": health,
        "articles": articles,
        "last_article_count": articles,
        "average_latency_ms": average_latency_ms,
        "current_backoff_seconds": current_backoff_seconds,
        "next_retry_at": next_retry_at,
        "backoff_active": bool(next_retry_at and (now or utc_now()) < next_retry_at),
        "cache_status": cache_status,
        "cached_article_count": cached_article_count,
    }
    if metadata:
        payload.update(metadata)
    payload["freshness_state"] = compute_freshness_state(payload, settings, enabled=enabled, now=now)
    return payload


def source_metadata_index(config: AppConfig) -> dict[str, dict[str, Any]]:
    index = {
        "GDELT": {
            "category": "Global News",
            "packages": ["global-news-starter", "geopolitics-starter"],
            "language": "en",
            "source_type": "api",
            "source_tier": 4,
            "source_role": "aggregator",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "reliability_score": 0.7,
            "ownership": "GDELT",
            "editorial_context": "Public web index aggregator; verify original publisher context.",
        },
        "Google News RSS": {
            "category": "Global News",
            "packages": ["global-news-starter"],
            "language": "en",
            "source_type": "aggregator",
            "source_tier": 4,
            "source_role": "aggregator",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "reliability_score": 0.65,
            "ownership": "Google News",
            "editorial_context": "Aggregator feed; verify original publisher context.",
        },
        "Yahoo Finance RSS": {
            "category": "Finance",
            "packages": ["finance-starter"],
            "language": "en",
            "source_type": "aggregator",
            "source_tier": 4,
            "source_role": "aggregator",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "reliability_score": 0.75,
            "ownership": "Yahoo",
            "editorial_context": "Finance aggregator feed; verify original publisher context.",
        },
        "Global Public RSS": {
            "category": "Global News",
            "packages": ["global-news-starter", "ai-industry-starter"],
            "language": "en",
            "source_type": "rss",
            "source_tier": 3,
            "source_role": "niche_media",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "reliability_score": 0.72,
            "ownership": "Public RSS group",
            "editorial_context": "User-configured public RSS group.",
        },
        "Official RSS": {
            "category": "Official/Government",
            "packages": ["official-gov-starter"],
            "language": config.app.output_language,
            "source_type": "rss",
            "source_tier": 1,
            "source_role": "official",
            "state_affiliated": True,
            "propaganda_risk": "low",
            "reliability_score": 0.9,
            "ownership": "Official RSS group",
            "editorial_context": "Official or primary source feed.",
        },
    }
    for item in config.sources.library:
        index[item.name] = _metadata_from_source(item)
    for item in config.sources.custom_sources:
        index[item.name] = _metadata_from_source(item)
    return index


def configured_source_records(
    config: AppConfig, source_states: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    source_states = source_states or {}
    records: list[dict[str, Any]] = []
    builtins = [
        ("GDELT", config.sources.gdelt.enabled),
        ("Google News RSS", config.sources.google_news_rss.enabled),
        ("Yahoo Finance RSS", config.sources.yahoo_finance_rss.enabled),
        ("Global Public RSS", config.sources.public_rss.enabled),
        ("Official RSS", config.sources.official_rss.enabled),
    ]
    metadata = source_metadata_index(config)
    for name, enabled in builtins:
        records.append(_record_for_source(name, metadata[name], enabled, source_states.get(name), config))
    enabled_packages = set(config.sources.enabled_packages)
    for item in config.sources.library:
        enabled = item.kind == "rss" and bool(item.enabled or enabled_packages.intersection(item.packages))
        records.append(
            _record_for_source(item.name, _metadata_from_source(item), enabled, source_states.get(item.name), config)
        )
    for item in config.sources.custom_sources:
        records.append(
            _record_for_source(
                item.name, _metadata_from_source(item), item.enabled, source_states.get(item.name), config
            )
        )
    return records


def source_summary(config: AppConfig, source_states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records = configured_source_records(config, source_states)
    enabled = [record for record in records if record["enabled"]]
    states = Counter(record["freshness_state"] for record in enabled)
    return {
        "configured_sources": len(records),
        "enabled_sources": len(enabled),
        "fresh": states.get("fresh", 0),
        "stale": states.get("stale", 0),
        "very_stale": states.get("very_stale", 0),
        "no_data": states.get("no_data", 0),
        "error": states.get("error", 0),
        "unknown": states.get("unknown", 0),
    }


def source_tier_distribution(config: AppConfig, source_states: dict[str, dict[str, Any]]) -> dict[str, int]:
    enabled = [record for record in configured_source_records(config, source_states) if record["enabled"]]
    counts = Counter(str(record.get("source_tier", 4)) for record in enabled)
    return {f"tier_{tier}": counts.get(str(tier), 0) for tier in range(1, 5)}


def top_failing_sources(source_states: dict[str, dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    failing = []
    for name, state in source_states.items():
        failures = int(state.get("failure_count") or state.get("consecutive_failures") or 0)
        if state.get("freshness_state") in {"error", "very_stale"} or failures:
            failing.append(
                {
                    "source": name,
                    "freshness_state": state.get("freshness_state", "unknown"),
                    "failure_count": failures,
                    "last_error_category": state.get("last_error_category"),
                    "last_failure_reason": state.get("last_failure_reason"),
                }
            )
    return sorted(failing, key=lambda item: item["failure_count"], reverse=True)[:limit]


def compute_intelligence_gaps(config: AppConfig, source_states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records = configured_source_records(config, source_states)
    group_results: list[dict[str, Any]] = []
    for package_id, preset in SOURCE_PACKAGE_PRESETS.items():
        group_records = [record for record in records if package_id in record.get("packages", [])]
        group_results.append(_gap_for_group(f"package:{package_id}", str(preset["name"]), group_records))
    for category in SOURCE_LIBRARY_CATEGORIES:
        if category == "Custom":
            continue
        group_records = [record for record in records if record.get("category") == category]
        group_results.append(_gap_for_group(f"category:{category}", category, group_records))
    for language in ["en", "zh-CN"]:
        group_records = [record for record in records if record.get("language") == language]
        group_results.append(_gap_for_group(f"language:{language}", f"Language {language}", group_records))
    focus_groups = {
        "Official/Government": ["Official/Government", "US", "Taiwan"],
        "Finance": ["Finance"],
        "China/Taiwan": ["China", "Taiwan"],
        "Semiconductor/AI": ["Semiconductor/AI"],
        "Company IR": ["Company IR"],
    }
    for label, categories in focus_groups.items():
        group_records = [record for record in records if record.get("category") in categories]
        group_results.append(_gap_for_group(f"focus:{label}", label, group_records, important=True))
    for topic in config.topics:
        if not topic.enabled:
            continue
        categories = topic_relevant_categories(topic.name, topic.prompt, topic.keywords)
        if not categories:
            continue
        group_records = [record for record in records if record.get("category") in categories]
        group_results.append(
            _gap_for_group(
                f"topic:{topic.name}",
                f"Topic coverage: {topic.name}",
                group_records,
                important=True,
                topic_categories=sorted(categories),
            )
        )
    summary = Counter(item["severity"] for item in group_results)
    return {
        "enabled": config.intelligence_gaps.enabled,
        "summary": {
            "healthy": summary.get("healthy", 0),
            "degraded": summary.get("degraded", 0),
            "critical": summary.get("critical", 0),
        },
        "healthy_groups": [item for item in group_results if item["severity"] == "healthy"],
        "degraded_groups": [item for item in group_results if item["severity"] == "degraded"],
        "critical_gaps": [item for item in group_results if item["severity"] == "critical"],
        "groups": group_results,
    }


def compute_coverage_quality(config: AppConfig, source_states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records = [record for record in configured_source_records(config, source_states) if record["enabled"]]
    fresh = [record for record in records if record["freshness_state"] == "fresh"]
    tier12 = [record for record in fresh if int(record.get("source_tier", 4)) <= 2]
    gaps = compute_intelligence_gaps(config, source_states)
    critical = len(gaps["critical_gaps"])
    degraded = len([group for group in gaps["degraded_groups"] if group.get("enabled_sources", 0) > 0])
    if not fresh:
        quality = "critical"
        reason = "No enabled source is currently fresh."
    elif critical:
        quality = "critical" if len(fresh) < 2 else "low"
        reason = f"{critical} critical intelligence gap(s) reduce confidence."
    elif len(fresh) < 2 or not tier12:
        quality = "low"
        reason = "Few fresh high-tier sources are available."
    elif degraded:
        quality = "medium"
        reason = f"{degraded} source group(s) are stale, empty, or degraded."
    else:
        quality = "high"
        reason = f"{len(fresh)} fresh sources and {len(tier12)} Tier 1/2 sources are available."
    return {
        "global": {
            "coverage_quality": quality,
            "reason": reason,
            "fresh_source_count": len(fresh),
            "enabled_source_count": len(records),
            "tier_1_2_fresh_count": len(tier12),
            "critical_gap_count": critical,
            "degraded_group_count": degraded,
            "recommended_action": _coverage_action(quality),
        },
        "topics": [_topic_coverage(topic, records, quality, reason) for topic in config.topics if topic.enabled],
    }


def source_package_status(config: AppConfig, source_states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = configured_source_records(config, source_states)
    enabled_packages = set(config.sources.enabled_packages)
    output = []
    for package_id, preset in SOURCE_PACKAGE_PRESETS.items():
        package_records = [record for record in records if package_id in record.get("packages", [])]
        enabled_records = [record for record in package_records if record["enabled"]]
        fresh_records = [record for record in enabled_records if record["freshness_state"] == "fresh"]
        failing_records = [record for record in enabled_records if record["freshness_state"] in {"error", "no_data"}]
        warnings = _source_package_warnings(package_id, enabled_packages, enabled_records, fresh_records)
        output.append(
            {
                "id": package_id,
                "name": preset["name"],
                "description": preset["description"],
                "expected_coverage": preset["expected_coverage"],
                "recommended_use_case": preset["recommended_use_case"],
                "source_count": len(package_records),
                "enabled_source_count": len(enabled_records),
                "fresh_source_count": len(fresh_records),
                "failing_source_count": len(failing_records),
                "enabled": package_id in enabled_packages,
                "source_names": [str(record.get("name")) for record in enabled_records],
                "warnings": warnings,
                "recommended_action": _source_package_action(package_id, enabled_packages, warnings),
                "last_package_test": _latest_package_test_time(enabled_records),
                "categories": preset["categories"],
                "suggested_refresh_interval_seconds": preset["suggested_refresh_interval_seconds"],
                "suggested_relevance_threshold": preset["suggested_relevance_threshold"],
                "topic_examples": preset["topic_examples"],
                "tier_weights": preset["tier_weights"],
            }
        )
    return output


def _latest_package_test_time(records: list[dict[str, Any]]) -> str | None:
    values = []
    for record in records:
        for key in ("last_fetch_time", "last_success_time", "last_failure_time"):
            parsed = parse_datetime(record.get(key))
            if parsed:
                values.append(parsed)
    if not values:
        return None
    return max(values).isoformat()


def _source_package_warnings(
    package_id: str,
    enabled_packages: set[str],
    enabled_records: list[dict[str, Any]],
    fresh_records: list[dict[str, Any]],
) -> list[str]:
    if package_id not in enabled_packages:
        if not enabled_packages:
            return ["No source packages are enabled; source coverage may be too narrow for production monitoring."]
        return []
    if not enabled_records:
        return ["This source package is enabled, but no matching sources are enabled."]
    if not fresh_records:
        return ["This source package is enabled, but none of its sources are currently fresh."]
    return []


def _source_package_action(package_id: str, enabled_packages: set[str], warnings: list[str]) -> str:
    if not warnings:
        return "No immediate action."
    if package_id not in enabled_packages:
        return "Enable at least one starter source package or add custom RSS/API sources."
    return "Test the package sources, wait for backoff to expire, or add another source package."


def topic_relevant_categories(name: str, prompt: str, keywords: list[str]) -> set[str]:
    text = " ".join([name, prompt, " ".join(keywords)]).casefold()
    categories: set[str] = set()
    if any(token in text for token in ["taiwan", "tsmc", "cross-strait"]):
        categories.update({"Taiwan", "Semiconductor/AI", "Official/Government"})
    if any(token in text for token in ["china", "xinhua", "rare earth", "export", "trade"]):
        categories.update({"China", "US", "Official/Government", "Finance"})
    if any(token in text for token in ["ai", "chip", "semiconductor", "nvidia", "asml"]):
        categories.update({"Semiconductor/AI", "Company IR"})
    if any(token in text for token in ["market", "stock", "finance", "earnings"]):
        categories.add("Finance")
    return categories


def next_backoff_seconds(
    previous_seconds: int,
    failure_count: int,
    *,
    default_interval_seconds: int,
    multiplier: float,
    max_backoff_minutes: int,
) -> int:
    base = max(default_interval_seconds, previous_seconds or default_interval_seconds)
    if failure_count <= 1 and not previous_seconds:
        return min(base, max_backoff_minutes * 60)
    return int(min(base * max(1.0, multiplier), max_backoff_minutes * 60))


def articles_to_cache_payload(articles: list[Article]) -> list[dict[str, Any]]:
    return [article_to_dict(article) for article in articles]


def articles_from_cache_payload(payload: list[dict[str, Any]], *, cache_status: str) -> list[Article]:
    articles = []
    for item in payload:
        articles.append(
            Article(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                source=str(item.get("source") or ""),
                published_at=parse_datetime(item.get("published_at")),
                snippet=item.get("snippet"),
                language=item.get("language"),
                raw=item.get("raw") if isinstance(item.get("raw"), dict) else None,
                reliability_score=float(item.get("reliability_score", 0.6)),
                ownership=item.get("ownership"),
                bias_hint=item.get("bias_hint"),
                category=item.get("category"),
                source_type=item.get("source_type"),
                source_url=item.get("source_url"),
                source_tier=int(item.get("source_tier", 4)),
                source_role=str(item.get("source_role", "custom")),  # type: ignore[arg-type]
                state_affiliated=bool(item.get("state_affiliated", False)),
                propaganda_risk=str(item.get("propaganda_risk", "unknown")),  # type: ignore[arg-type]
                editorial_context=item.get("editorial_context"),
                is_cached=True,
                cache_status=cache_status,
            )
        )
    return [article for article in articles if article.title and article.url]


def article_to_dict(article: Article) -> dict[str, Any]:
    payload = asdict(article)
    payload["published_at"] = article.published_at.isoformat() if article.published_at else None
    return payload


def article_cache_key(article: Article, topic_name: str) -> str:
    return f"{topic_name}:{normalize_url(article.url)}"


def confirmation_key(article: Article) -> str:
    words = [word for word in re.findall(r"[A-Za-z0-9]+", article.title.casefold()) if len(word) > 3]
    day = article.published_at.date().isoformat() if article.published_at else ""
    return f"{day}:{' '.join(sorted(words[:10])[:8])}" or normalize_url(article.url)


def source_owner_key(article: Article) -> str:
    return (article.ownership or article.source or "").casefold().strip()


def _metadata_from_source(item: Any) -> dict[str, Any]:
    return {
        "category": getattr(item, "category", "Custom"),
        "packages": list(getattr(item, "packages", []) or []),
        "language": getattr(item, "language", None) or getattr(item, "default_language", None) or "en",
        "source_type": getattr(item, "source_type", None) or getattr(item, "kind", "rss"),
        "source_tier": int(getattr(item, "source_tier", 4)),
        "source_role": getattr(item, "source_role", "custom"),
        "state_affiliated": bool(getattr(item, "state_affiliated", False)),
        "propaganda_risk": getattr(item, "propaganda_risk", "unknown"),
        "reliability_score": float(getattr(item, "reliability_score", 0.6)),
        "ownership": getattr(item, "ownership", None),
        "bias_hint": getattr(item, "bias_hint", None),
        "editorial_context": getattr(item, "editorial_context", ""),
        "website_url": getattr(item, "website_url", None),
        "help_url": getattr(item, "help_url", None),
    }


def _record_for_source(
    name: str,
    metadata: dict[str, Any],
    enabled: bool,
    state: dict[str, Any] | None,
    config: AppConfig,
) -> dict[str, Any]:
    record = {"name": name, "enabled": enabled, **metadata}
    if state:
        record.update(state)
    record["freshness_state"] = compute_freshness_state(record, config.source_health, enabled=enabled)
    return record


def _gap_for_group(
    group_id: str,
    label: str,
    records: list[dict[str, Any]],
    *,
    important: bool = False,
    topic_categories: list[str] | None = None,
) -> dict[str, Any]:
    enabled = [record for record in records if record.get("enabled")]
    fresh = [record for record in enabled if record.get("freshness_state") == "fresh"]
    degraded = [
        record
        for record in enabled
        if record.get("freshness_state") in {"stale", "very_stale", "no_data", "error", "unknown"}
    ]
    if not enabled:
        severity = "critical" if important or label in IMPORTANT_GROUPS else "degraded"
        reason = "No enabled sources are available for this group."
        action = "Enable a source package or add a public RSS/API source for this group."
    elif not fresh:
        severity = "critical"
        reason = f"{len(enabled)} enabled source(s), but none are fresh."
        action = "Test sources, wait for backoff to expire, or add another high-tier source."
    elif degraded:
        severity = "degraded"
        reason = f"{len(fresh)} fresh source(s), {len(degraded)} stale, empty, or failing source(s)."
        action = "Review stale/failing sources and add higher-tier confirmation where needed."
    else:
        severity = "healthy"
        reason = f"{len(fresh)} fresh source(s)."
        action = "No immediate action."
    return {
        "id": group_id,
        "name": label,
        "severity": severity,
        "enabled_sources": len(enabled),
        "fresh_sources": len(fresh),
        "degraded_sources": len(degraded),
        "reason": reason,
        "recommended_action": action,
        "topic_relevant_categories": topic_categories or [],
    }


def _coverage_action(quality: str) -> str:
    if quality == "high":
        return "Continue monitoring."
    if quality == "medium":
        return "Review degraded groups and source freshness."
    if quality == "low":
        return "Enable more Tier 1/2 or topic-relevant public sources."
    return "Do not interpret silence as no news; fix critical gaps before relying on the monitor."


def _topic_coverage(
    topic: Any, records: list[dict[str, Any]], fallback_quality: str, fallback_reason: str
) -> dict[str, Any]:
    categories = topic_relevant_categories(topic.name, topic.prompt, topic.keywords)
    topic_records = [record for record in records if record.get("category") in categories] if categories else records
    fresh = [record for record in topic_records if record.get("freshness_state") == "fresh"]
    if not topic_records or not fresh:
        quality = "critical"
        reason = "No fresh source coverage for topic-relevant categories."
    elif len(fresh) < 2:
        quality = "low"
        reason = "Only one fresh topic-relevant source is available."
    else:
        quality = fallback_quality
        reason = fallback_reason
    return {
        "topic": topic.name,
        "coverage_quality": quality,
        "reason": reason,
        "fresh_source_count": len(fresh),
        "topic_relevant_categories": sorted(categories),
        "recommended_action": _coverage_action(quality),
    }
