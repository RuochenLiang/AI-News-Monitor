from __future__ import annotations

from datetime import datetime
from typing import Any

from src.utils.time_utils import utc_now

REJECTION_REASONS = {
    "no_keyword_match",
    "unsupported_language",
    "duplicate",
    "source_stale",
    "score_below_threshold",
    "llm_relevance_low",
    "rate_limit",
    "cooldown",
    "max_alerts_per_hour",
    "missing_notifier",
    "notification_failed",
    "source_package_disabled",
    "coverage_critical",
}


def new_pipeline_funnel(*, mode: str = "normal", test_mode: bool = False) -> dict[str, Any]:
    started = utc_now()
    return {
        "mode": mode,
        "test_mode": test_mode,
        "result": "running",
        "cycle_started_at": started,
        "cycle_finished_at": None,
        "cycle_duration_seconds": None,
        "sources_attempted": 0,
        "sources_succeeded": 0,
        "sources_failed": 0,
        "sources_skipped_backoff": 0,
        "articles_fetched": 0,
        "articles_after_deduplication": 0,
        "articles_accepted_by_language": 0,
        "articles_rejected_by_language": 0,
        "articles_keyword_matched": 0,
        "articles_rejected_by_keyword": 0,
        "articles_rejected_as_duplicates": 0,
        "candidates_ranked": 0,
        "candidates_sent_to_llm": 0,
        "llm_accepted": 0,
        "llm_rejected": 0,
        "rejected_below_threshold": 0,
        "alerts_saved": 0,
        "notifications_attempted": 0,
        "notifications_succeeded": 0,
        "notifications_failed": 0,
        "rejection_reasons": {},
        "top_rejection_reasons": [],
        "top_rejected_candidate": None,
        "topic_threshold": None,
        "concise_summary": "Fetched 0 -> Language 0 -> Keyword 0 -> New 0 -> LLM 0 -> Alerts 0",
        "zero_alert_explanation": "Cycle is still running.",
        "recommended_action": None,
    }


def increment(funnel: dict[str, Any] | None, key: str, amount: int = 1) -> None:
    if funnel is None:
        return
    if amount <= 0:
        return
    funnel[key] = int(funnel.get(key) or 0) + amount


def reject(funnel: dict[str, Any] | None, reason: str, amount: int = 1) -> None:
    if funnel is None:
        return
    if amount <= 0:
        return
    if reason not in REJECTION_REASONS:
        reason = "llm_relevance_low"
    reasons = funnel.setdefault("rejection_reasons", {})
    reasons[reason] = int(reasons.get(reason) or 0) + amount


def record_rejected_candidate(
    funnel: dict[str, Any] | None,
    *,
    title: str,
    source: str,
    score: int,
    threshold: int,
) -> None:
    if funnel is None:
        return
    current = funnel.get("top_rejected_candidate")
    if current and int(current.get("score") or 0) >= score:
        return
    funnel["top_rejected_candidate"] = {
        "title": title,
        "source": source,
        "score": score,
        "threshold": threshold,
    }


def finish(funnel: dict[str, Any] | None) -> dict[str, Any]:
    if funnel is None:
        return {}
    finished = utc_now()
    started = _as_datetime(funnel.get("cycle_started_at"))
    funnel["cycle_finished_at"] = finished
    if started:
        funnel["cycle_duration_seconds"] = round((finished - started).total_seconds(), 3)
    funnel["top_rejection_reasons"] = [
        {"reason": reason, "count": count}
        for reason, count in sorted(
            (funnel.get("rejection_reasons") or {}).items(), key=lambda item: item[1], reverse=True
        )
    ][:8]
    funnel["concise_summary"] = concise_summary(funnel)
    funnel["zero_alert_explanation"] = zero_alert_explanation(funnel)
    funnel["recommended_action"] = recommended_action(funnel)
    funnel["result"] = result_status(funnel)
    return funnel


def concise_summary(funnel: dict[str, Any]) -> str:
    return (
        f"Fetched {int(funnel.get('articles_fetched') or 0)} -> "
        f"Language {int(funnel.get('articles_accepted_by_language') or 0)} -> "
        f"Keyword {int(funnel.get('articles_keyword_matched') or 0)} -> "
        f"New {int(funnel.get('candidates_ranked') or 0)} -> "
        f"LLM {int(funnel.get('candidates_sent_to_llm') or 0)} -> "
        f"Alerts {int(funnel.get('alerts_saved') or 0)}"
    )


def zero_alert_explanation(funnel: dict[str, Any]) -> str:
    if int(funnel.get("alerts_saved") or 0) > 0:
        sent = int(funnel.get("notifications_succeeded") or 0)
        attempted = int(funnel.get("notifications_attempted") or 0)
        reasons = {str(item.get("reason")) for item in funnel.get("top_rejection_reasons") or []}
        if "missing_notifier" in reasons:
            return "Alert pipeline succeeded, but no notification channel is ready."
        if attempted and sent == 0:
            return "Alert was saved, but notification delivery failed."
        return "At least one alert was saved."
    reasons = funnel.get("top_rejection_reasons") or []
    if not reasons:
        if int(funnel.get("articles_fetched") or 0) == 0:
            return "No articles were fetched."
        return "No alert passed all pipeline stages."
    top = reasons[0]
    reason = str(top.get("reason") or "")
    count = int(top.get("count") or 0)
    if reason == "score_below_threshold":
        candidate = funnel.get("top_rejected_candidate") or {}
        score = candidate.get("score")
        threshold = candidate.get("threshold") or funnel.get("topic_threshold")
        return f"No alerts because {count} candidate(s) were below threshold. Top score {score}; threshold {threshold}."
    if reason == "no_keyword_match":
        return f"No alerts because {count} article(s) did not match topic keywords."
    if reason == "duplicate":
        return f"No alerts because {count} article(s) were already seen, processed, or duplicated."
    if reason == "unsupported_language":
        return f"No alerts because {count} article(s) used unsupported languages."
    if reason == "llm_relevance_low":
        return f"No alerts because LLM rejected {count} candidate(s) as not actionable."
    if reason == "missing_notifier":
        return "Alert was saved, but no enabled notifier was available."
    if reason == "notification_failed":
        return "Alert was saved, but all notification attempts failed."
    return f"No alerts. Top rejection reason: {reason} ({count})."


def recommended_action(funnel: dict[str, Any]) -> str | None:
    if int(funnel.get("alerts_saved") or 0) > 0:
        if int(funnel.get("notifications_attempted") or 0) and int(funnel.get("notifications_succeeded") or 0) == 0:
            return "Check notification channel diagnostics and retry the E2E test."
        return "No action needed for this cycle."
    reasons = {str(item.get("reason")) for item in funnel.get("top_rejection_reasons") or []}
    if "score_below_threshold" in reasons:
        return "For E2E testing, use Test Mode or a temporary threshold around 50-60. For production, keep thresholds high to reduce noise."
    if "no_keyword_match" in reasons:
        return "Review topic keywords or enable broad search only if the topic can tolerate more noise."
    if "missing_notifier" in reasons or "notification_failed" in reasons:
        return "Configure and test at least one notification channel in the desktop app."
    if "rate_limit" in reasons:
        return "Wait for source backoff to expire or add alternative public sources."
    return "Review the pipeline details and source coverage before treating silence as no news."


def result_status(funnel: dict[str, Any]) -> str:
    alerts = int(funnel.get("alerts_saved") or 0)
    attempted = int(funnel.get("notifications_attempted") or 0)
    succeeded = int(funnel.get("notifications_succeeded") or 0)
    reasons = set((funnel.get("rejection_reasons") or {}).keys())
    if "missing_notifier" in reasons and alerts > 0:
        return "partial"
    if funnel.get("test_mode"):
        if alerts > 0 and (succeeded > 0 or attempted == 0):
            return "success" if succeeded > 0 else "partial"
        if alerts > 0:
            return "partial"
        return "failed"
    if alerts > 0:
        return "success" if (succeeded > 0 or attempted == 0) else "partial"
    return "partial" if int(funnel.get("articles_fetched") or 0) > 0 else "failed"


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None
