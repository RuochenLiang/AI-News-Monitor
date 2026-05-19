from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from src.bias import annotate_bias_context, cluster_articles
from src.config import load_config
from src.dedupe import dedupe_articles
from src.diagnostics import classify_feed_http_error
from src.language import detect_supported_language, normalize_language
from src.llm_client import LLMClient
from src.logging_setup import alert_logger, cleanup_old_logs
from src.models import (
    Alert,
    AppConfig,
    Article,
    LLMAnalysis,
    MarketWatchSuggestion,
    NotificationResult,
    NotifierSettings,
    RuntimeStatus,
    TopicConfig,
)
from src.notifiers import (
    EmailNotifier,
    GenericWebhookNotifier,
    Notifier,
    RelayWebhookNotifier,
    TelegramNotifier,
    WeComNotifier,
)
from src.pipeline import finish, increment, new_pipeline_funnel, record_rejected_candidate, reject
from src.scoring import cooldown_allows_alert, hourly_rate_limit_allows_alert, rank_articles, topic_threshold
from src.source_reliability import (
    articles_from_cache_payload,
    articles_to_cache_payload,
    compute_coverage_quality,
    compute_freshness_state,
    compute_intelligence_gaps,
    next_backoff_seconds,
    source_metadata_index,
    source_state_payload,
    source_summary,
    source_tier_distribution,
    top_failing_sources,
)
from src.sources import (
    CustomRssSource,
    GdeltSource,
    GoogleNewsRssSource,
    NewsSource,
    OfficialRssSource,
    PublicRssSource,
    YahooFinanceRssSource,
)
from src.sources.library import enabled_library_sources
from src.storage import SQLiteStore
from src.translation import enrich_article_language
from src.utils.text_utils import keyword_matches
from src.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

StatusCallback = Callable[[RuntimeStatus], None]
LogCallback = Callable[[str], None]
EventCallback = Callable[[dict], None]


class NewsMonitor:
    def __init__(
        self,
        config_path: Path,
        runtime_dir: Path,
        store: SQLiteStore | None = None,
        source_factory: Callable[[AppConfig], list[NewsSource]] | None = None,
        llm_factory: Callable[[AppConfig], LLMClient] | None = None,
        notifier_factory: Callable[[NotifierSettings, int], list[Notifier]] | None = None,
        status_callback: StatusCallback | None = None,
        log_callback: LogCallback | None = None,
        event_callback: EventCallback | None = None,
    ):
        self.config_path = config_path
        self.runtime_dir = runtime_dir
        self.store = store or SQLiteStore(runtime_dir / "data" / "monitor.sqlite")
        self.source_factory = source_factory or build_sources
        self.llm_factory = llm_factory or (lambda config: LLMClient(config.llm))
        self.notifier_factory = notifier_factory or build_notifiers
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.event_callback = event_callback
        self.status = RuntimeStatus()
        self._alerts_logger = alert_logger(runtime_dir)
        self._last_topic_run_at: dict[str, datetime] = {}

    def run_cycle(self) -> RuntimeStatus:
        return self._run_cycle()

    def run_e2e_test(self) -> RuntimeStatus:
        run_id = str(int(time.time() * 1000))
        topic = TopicConfig(
            name="E2E Test Mode",
            enabled=True,
            prompt=(
                "Test-only pipeline verification. Treat the controlled article as actionable only for verifying "
                "fetch, candidate, LLM, alert, and notification flow."
            ),
            keywords=["OpenAI", "NVIDIA", "AI infrastructure partnership"],
            output_language="en",
            min_relevance_score=50,
        )
        return self._run_cycle(
            mode="e2e_test",
            test_mode=True,
            active_topics_override=[topic],
            sources_override=[E2ETestSource(run_id)],
            llm_client_override=E2ETestLlmClient(),
            use_source_cache=False,
        )

    def _run_cycle(
        self,
        *,
        mode: str = "normal",
        test_mode: bool = False,
        active_topics_override: list[TopicConfig] | None = None,
        sources_override: list[NewsSource] | None = None,
        llm_client_override: object | None = None,
        notifiers_override: list[Notifier] | None = None,
        use_source_cache: bool = True,
    ) -> RuntimeStatus:
        config = load_config(self.config_path)
        cleanup_old_logs(self.runtime_dir, config.monitor.log_retention_days)
        active_topics = (
            active_topics_override
            if active_topics_override is not None
            else [topic for topic in config.topics if topic.enabled]
        )
        sources = sources_override if sources_override is not None else self.source_factory(config)
        llm_client = llm_client_override if llm_client_override is not None else self.llm_factory(config)
        notifiers = (
            notifiers_override
            if notifiers_override is not None
            else self.notifier_factory(config.notifiers, config.monitor.request_timeout_seconds)
        )
        funnel = new_pipeline_funnel(mode=mode, test_mode=test_mode)
        self.status.pipeline_funnel = funnel
        if test_mode:
            self.status.e2e_result = funnel
        self._refresh_notifier_health(notifiers, config)

        self.status.active_topics_count = len(active_topics)
        self.status.output_language = config.app.output_language
        self.status.alert_mode = config.alerts.default_mode
        self.status.source_packages_enabled = list(config.sources.enabled_packages)
        self.status.llm_health = "configured" if getattr(llm_client, "api_key", None) else "missing_api_key"
        self.status.latest_articles_fetched = 0
        self.status.latest_candidates = 0
        self.status.queue_length = 0
        self.status.source_states = self.store.load_all_source_states()
        self._refresh_reliability_status(config)
        self.status.recent_matches = []
        self.status.alerts_sent_today = self.store.alerts_sent_today()
        self.status.last_fetch_time = utc_now()
        self._emit_status()
        self._publish({"type": "cycle_started", "active_topics": len(active_topics), "mode": mode})
        self._log(f"Monitoring cycle started for {len(active_topics)} active topics.")

        for raw_topic in active_topics:
            topic = replace(raw_topic, output_language=config.app.output_language)
            if test_mode:
                topic = replace(raw_topic, output_language="en")
            if not self._topic_due(topic):
                self._log(f"Topic '{topic.name}' skipped until its poll interval elapses.")
                continue
            threshold = topic_threshold(topic, config.monitor.min_relevance_score)
            funnel["topic_threshold"] = threshold
            topic_articles = self._fetch_topic_articles(
                sources, topic, config, funnel, use_source_cache=use_source_cache
            )
            self._last_topic_run_at[topic.name] = utc_now()
            self.status.latest_articles_fetched += len(topic_articles)
            unique_articles = dedupe_articles(topic_articles)
            duplicate_count = max(0, len(topic_articles) - len(unique_articles))
            increment(funnel, "articles_rejected_as_duplicates", duplicate_count)
            reject(funnel, "duplicate", duplicate_count)
            increment(funnel, "articles_after_deduplication", len(unique_articles))
            candidates = self._candidate_articles(unique_articles, topic, config, funnel, skip_seen_dedupe=test_mode)
            cluster_articles(candidates, config.bias.min_cluster_size)
            candidates = rank_articles(candidates, topic, config.quality, preferred_language=config.app.output_language)
            increment(funnel, "candidates_ranked", len(candidates))
            self.status.latest_candidates += len(candidates)
            self.status.queue_length = len(candidates)
            self._log(f"Topic '{topic.name}' fetched {len(topic_articles)} articles, {len(candidates)} candidates.")
            candidate_limit = config.fetching.max_candidate_articles_per_topic
            for article in candidates[:candidate_limit]:
                self.status.recent_matches.insert(
                    0,
                    {
                        "topic": topic.name,
                        "title": article.title,
                        "url": article.url,
                        "score": article.ranking_score,
                        "source": article.source,
                        "reason": article.selection_reason,
                    },
                )
                self.status.recent_matches = self.status.recent_matches[:25]
                self._publish(
                    {
                        "type": "candidate_ranked",
                        "topic": topic.name,
                        "title": article.title,
                        "url": article.url,
                        "ranking_score": article.ranking_score,
                        "source": article.source,
                    }
                )
            self._analyze_candidates(candidates[:candidate_limit], topic, config, llm_client, notifiers, funnel)

        self.status.alerts_sent_today = self.store.alerts_sent_today()
        self.status.queue_length = 0
        self._refresh_reliability_status(config)
        self.status.pipeline_funnel = finish(funnel)
        if test_mode:
            self.status.e2e_result = self.status.pipeline_funnel
        self._emit_status()
        self._publish(
            {
                "type": "cycle_completed",
                "alerts_sent_today": self.status.alerts_sent_today,
                "mode": mode,
                "pipeline": self.status.pipeline_funnel.get("concise_summary"),
                "result": self.status.pipeline_funnel.get("result"),
            }
        )
        self._log("Monitoring cycle completed.")
        return self.status

    def _topic_due(self, topic: TopicConfig) -> bool:
        if not topic.poll_interval_seconds:
            return True
        last_run_at = self._last_topic_run_at.get(topic.name)
        if not last_run_at:
            return True
        return utc_now() - last_run_at >= timedelta(seconds=topic.poll_interval_seconds)

    def _fetch_topic_articles(
        self,
        sources: list[NewsSource],
        topic: TopicConfig,
        config: AppConfig,
        funnel: dict | None = None,
        *,
        use_source_cache: bool = True,
    ) -> list[Article]:
        articles: list[Article] = []
        metadata = source_metadata_index(config)
        cycle_deadline = time.monotonic() + config.fetching.overall_cycle_deadline_seconds
        for source in sources:
            if time.monotonic() >= cycle_deadline:
                self._log("Overall source cycle deadline reached; remaining sources skipped.")
                break
            now = utc_now()
            previous_state = self.store.load_source_state(source.name) or self.status.source_states.get(source.name, {})
            next_retry_at = _parse_status_time(previous_state.get("next_retry_at"))
            if config.smart_polling.enabled and next_retry_at and now < next_retry_at:
                state = {
                    **previous_state,
                    "enabled": True,
                    "backoff_active": True,
                    "freshness_state": compute_freshness_state(previous_state, config.source_health, now=now),
                }
                self.status.source_states[source.name] = state
                increment(funnel, "sources_skipped_backoff")
                reject(funnel, "source_stale")
                self._log(f"Source {source.name} skipped; backoff active until {next_retry_at.isoformat()}.")
                continue
            cache_key = _source_cache_key(source.name, topic.name)
            cached = (
                self.store.load_source_cache(cache_key) if config.source_cache.enabled and use_source_cache else None
            )
            if cached and cached.get("cached_at"):
                cache_age = now - cached["cached_at"]
                if cache_age <= timedelta(seconds=config.source_cache.source_ttl_seconds):
                    cached_articles = articles_from_cache_payload(cached["articles"], cache_status="cache_hit")
                    increment(funnel, "sources_attempted")
                    increment(funnel, "sources_succeeded")
                    increment(funnel, "articles_fetched", len(cached_articles))
                    state = source_state_payload(
                        source_name=source.name,
                        metadata=metadata.get(source.name),
                        enabled=True,
                        health="ok",
                        articles=len(cached_articles),
                        last_fetch_time=now,
                        last_success_time=now,
                        failure_count=0,
                        cache_status="cache_hit",
                        cached_article_count=len(cached_articles),
                        settings=config.source_health,
                        now=now,
                    )
                    self._record_source_state(source.name, state)
                    self.status.source_health[source.name] = f"ok cache_hit ({len(cached_articles)} articles)"
                    articles.extend(cached_articles)
                    continue
            try:
                logger.info("Source fetch started: %s topic=%s", source.name, topic.name)
                increment(funnel, "sources_attempted")
                started = time.perf_counter()
                fetched = source.fetch(topic)
                latency_ms = int((time.perf_counter() - started) * 1000)
                if config.fetching.max_articles_per_source:
                    fetched = fetched[: config.fetching.max_articles_per_source]
                articles.extend(fetched)
                increment(funnel, "sources_succeeded")
                increment(funnel, "articles_fetched", len(fetched))
                self.status.last_successful_source_fetch = now
                self.status.source_health[source.name] = f"ok ({len(fetched)} articles)"
                if config.source_cache.enabled:
                    self.store.save_source_cache(cache_key, source.name, topic.name, articles_to_cache_payload(fetched))
                state = source_state_payload(
                    source_name=source.name,
                    metadata=metadata.get(source.name),
                    enabled=True,
                    health="ok",
                    articles=len(fetched),
                    last_fetch_time=now,
                    last_success_time=now,
                    last_failure_time=None,
                    last_failure_reason=None,
                    last_error_category=None,
                    failure_count=0,
                    average_latency_ms=latency_ms,
                    current_backoff_seconds=0,
                    next_retry_at=None,
                    cache_status="updated" if config.source_cache.enabled else None,
                    settings=config.source_health,
                    now=now,
                )
                self._record_source_state(source.name, state)
                logger.info("Source fetch completed: %s articles=%s", source.name, len(fetched))
                self._publish({"type": "source_fetch", "source": source.name, "articles": len(fetched), "ok": True})
            except Exception as exc:  # noqa: BLE001 - one source must not stop monitor
                self.status.error_message = f"{source.name}: {exc}"
                error_category = _classify_source_exception(exc)
                increment(funnel, "sources_failed")
                if error_category == "api_rate_limited":
                    reject(funnel, "rate_limit")
                failure_count = int(previous_state.get("failure_count") or 0) + 1
                previous_backoff = int(previous_state.get("current_backoff_seconds") or 0)
                backoff_seconds = (
                    next_backoff_seconds(
                        previous_backoff,
                        failure_count,
                        default_interval_seconds=config.monitor.default_interval_seconds,
                        multiplier=config.smart_polling.failure_backoff_multiplier,
                        max_backoff_minutes=config.smart_polling.max_backoff_minutes,
                    )
                    if config.smart_polling.enabled
                    else 0
                )
                retry_at = now + timedelta(seconds=backoff_seconds) if backoff_seconds else None
                cached_articles = self._last_known_good_articles(cached, config, now)
                if cached_articles:
                    articles.extend(cached_articles)
                self.status.source_health[source.name] = (
                    f"{_source_error_summary(source.name, error_category, exc)} with last_known_good ({len(cached_articles)} articles)"
                    if cached_articles
                    else _source_error_summary(source.name, error_category, exc)
                )
                state = source_state_payload(
                    source_name=source.name,
                    metadata=metadata.get(source.name),
                    enabled=True,
                    health="error",
                    articles=len(cached_articles),
                    last_fetch_time=now,
                    last_success_time=_parse_status_time(previous_state.get("last_success_time")),
                    last_failure_time=now,
                    last_failure_reason=str(exc),
                    last_error_category=error_category,
                    failure_count=failure_count,
                    current_backoff_seconds=backoff_seconds,
                    next_retry_at=retry_at,
                    cache_status="last_known_good" if cached_articles else None,
                    cached_article_count=len(cached_articles),
                    settings=config.source_health,
                    now=now,
                )
                self._record_source_state(source.name, state)
                logger.exception("Source fetch failed: %s", source.name)
                self._log(f"Source {source.name} failed: {_source_error_summary(source.name, error_category, exc)}")
                self._publish(
                    {
                        "type": "source_fetch",
                        "source": source.name,
                        "ok": False,
                        "category": error_category,
                        "summary": _source_error_summary(source.name, error_category, exc),
                    }
                )
                self._refresh_reliability_status(config)
                self._emit_status()
        return articles

    def _candidate_articles(
        self,
        articles: list[Article],
        topic: TopicConfig,
        config: AppConfig,
        funnel: dict | None = None,
        *,
        skip_seen_dedupe: bool = False,
    ) -> list[Article]:
        dedupe_hours = config.monitor.deduplicate_hours
        cutoff = utc_now() - timedelta(hours=dedupe_hours)
        candidates: list[Article] = []
        allowed_languages = {normalize_language(item) for item in config.enrichment.allowed_languages}
        for article in articles:
            if article.is_cached and not config.source_cache.allow_cached_alerts:
                reject(funnel, "source_stale")
                continue
            if article.is_cached and self.store.has_alert_for_article(article, topic.name):
                reject(funnel, "duplicate")
                increment(funnel, "articles_rejected_as_duplicates")
                continue
            article.language = detect_supported_language(article.title, article.snippet, fallback=article.language)
            if article.language not in allowed_languages:
                increment(funnel, "articles_rejected_by_language")
                reject(funnel, "unsupported_language")
                self._log(f"Unsupported language skipped for '{article.title}': {article.language or 'unknown'}")
                continue
            increment(funnel, "articles_accepted_by_language")
            if article.published_at and article.published_at < cutoff:
                reject(funnel, "source_stale")
                continue
            if not topic.broad_search:
                combined = f"{article.title}\n{article.snippet or ''}"
                if not keyword_matches(combined, topic.keywords):
                    increment(funnel, "articles_rejected_by_keyword")
                    reject(funnel, "no_keyword_match")
                    continue
            increment(funnel, "articles_keyword_matched")
            if not skip_seen_dedupe:
                if self.store.is_processed(article, topic.name):
                    increment(funnel, "articles_rejected_as_duplicates")
                    reject(funnel, "duplicate")
                    continue
                if self.store.seen_similar_recently(article, topic.name, dedupe_hours):
                    increment(funnel, "articles_rejected_as_duplicates")
                    reject(funnel, "duplicate")
                    continue
            candidates.append(article)
        return candidates

    def _record_source_state(self, source_name: str, state: dict) -> None:
        self.status.source_states[source_name] = state
        self.store.save_source_state(source_name, state)

    def _last_known_good_articles(self, cached: dict | None, config: AppConfig, now: datetime) -> list[Article]:
        if not cached or not config.source_cache.last_known_good_enabled:
            return []
        cached_at = cached.get("last_known_good_at") or cached.get("cached_at")
        if not cached_at:
            return []
        if now - cached_at > timedelta(hours=config.source_cache.last_known_good_max_age_hours):
            return []
        return articles_from_cache_payload(cached.get("articles", []), cache_status="last_known_good")

    def _refresh_reliability_status(self, config: AppConfig) -> None:
        self.status.source_summary = source_summary(config, self.status.source_states)
        self.status.source_cache_summary = _cache_summary(self.status.source_states)
        self.status.source_backoff_summary = _backoff_summary(self.status.source_states)
        self.status.source_tier_distribution = source_tier_distribution(config, self.status.source_states)
        self.status.top_failing_sources = top_failing_sources(self.status.source_states)
        self.status.intelligence_gaps = compute_intelligence_gaps(config, self.status.source_states)
        self.status.coverage_quality = compute_coverage_quality(config, self.status.source_states)

    def _analyze_candidates(
        self,
        candidates: list[Article],
        topic: TopicConfig,
        config: AppConfig,
        llm_client: object,
        notifiers: list[Notifier],
        funnel: dict | None = None,
    ) -> None:
        annotate_bias_context(candidates, config.bias.enabled, config.bias.mode, config.bias.min_cluster_size)
        for article in candidates:
            self.status.queue_length = max(0, self.status.queue_length - 1)
            self.store.upsert_article(article, topic.name)
            enrich_article_language(
                article,
                target_language=config.enrichment.target_language or topic.output_language,
                translation_enabled=config.enrichment.translation_enabled,
                summary_enabled=config.enrichment.summary_enabled,
                llm_client=llm_client,
            )
            try:
                logger.info("LLM analysis started: topic=%s title=%s", topic.name, article.title)
                increment(funnel, "candidates_sent_to_llm")
                analysis = llm_client.analyze_article(topic, article)
                self.status.last_llm_analysis_time = utc_now()
                logger.info("LLM analysis completed: score=%s topic=%s", analysis.relevance_score, topic.name)
            except Exception as exc:  # noqa: BLE001 - bad LLM output should not crash monitor
                increment(funnel, "llm_rejected")
                reject(funnel, "llm_relevance_low")
                logger.exception("LLM analysis failed for article: %s", article.title)
                self._log(f"LLM analysis failed for '{article.title}': {exc}")
                self.store.mark_processed(article, topic.name)
                self.status.total_articles_processed += 1
                self._emit_status()
                continue

            self.store.mark_processed(article, topic.name)
            self.status.total_articles_processed += 1
            threshold = topic_threshold(topic, config.monitor.min_relevance_score)
            if not analysis.is_actionable_alert:
                increment(funnel, "llm_rejected")
                reject(funnel, "llm_relevance_low")
                continue
            if analysis.relevance_score < threshold:
                increment(funnel, "rejected_below_threshold")
                reject(funnel, "score_below_threshold")
                record_rejected_candidate(
                    funnel,
                    title=article.title,
                    source=article.source,
                    score=analysis.relevance_score,
                    threshold=threshold,
                )
                continue
            increment(funnel, "llm_accepted")
            if not cooldown_allows_alert(self.store, topic):
                reject(funnel, "cooldown")
                self._log(f"Cooldown skipped alert for topic '{topic.name}'.")
                continue
            if not hourly_rate_limit_allows_alert(self.store, config.monitor.max_alerts_per_hour):
                reject(funnel, "max_alerts_per_hour")
                self._log("Hourly alert limit reached; alert skipped.")
                continue

            alert = Alert(
                topic_name=topic.name,
                article=article,
                analysis=analysis,
                sent_at=utc_now(),
                mode=config.alerts.default_mode,
                output_language=config.app.output_language,
            )
            alert.id = self.store.save_alert(alert)
            increment(funnel, "alerts_saved")
            self.status.last_alert_sent_time = alert.sent_at
            self.status.recent_alerts.insert(0, alert)
            self.status.recent_alerts = self.status.recent_alerts[:10]
            self._alerts_logger.info(
                "Alert saved: topic=%s score=%s title=%s", topic.name, analysis.relevance_score, alert.title
            )
            self._send_notifications(alert, notifiers, config, funnel)
            self._publish(
                {
                    "type": "alert_sent",
                    "topic": topic.name,
                    "title": alert.title,
                    "url": alert.article.url,
                    "relevance_score": analysis.relevance_score,
                }
            )
            self._emit_status()

    def _send_notifications(
        self, alert: Alert, notifiers: list[Notifier], config: AppConfig, funnel: dict | None = None
    ) -> None:
        if not notifiers:
            reject(funnel, "missing_notifier")
            self._log("No enabled notifiers configured; alert stored only.")
            return
        if config.notifications.fallback_enabled:
            for notifier in self._ordered_notifiers(notifiers, config.notifications.fallback_order):
                result = self._send_with_retry(
                    alert, notifier, config.notifications.retry_attempts, config.notifications.retry_base_delay_seconds
                )
                self._record_notification_result(alert, result, funnel)
                if result.success:
                    return
            self._log("All notification fallback channels failed; alert remains stored locally.")
            return
        for notifier in notifiers:
            result = self._send_with_retry(
                alert, notifier, config.notifications.retry_attempts, config.notifications.retry_base_delay_seconds
            )
            self._record_notification_result(alert, result, funnel)

    def _send_with_retry(
        self,
        alert: Alert,
        notifier: Notifier,
        retry_attempts: int,
        base_delay_seconds: float,
    ) -> NotificationResult:
        attempts = max(1, retry_attempts)
        result = NotificationResult(getattr(notifier, "name", "Notifier"), False, "Not attempted.")
        for attempt in range(1, attempts + 1):
            result = notifier.send(alert)
            if result.success:
                return result
            if attempt < attempts and base_delay_seconds > 0:
                time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
        return result

    def _record_notification_result(self, alert: Alert, result: NotificationResult, funnel: dict | None = None) -> None:
        increment(funnel, "notifications_attempted")
        self.status.notifier_health[result.notifier_name] = "ok" if result.success else f"error: {result.error_message}"
        state = self.status.notifier_states.setdefault(
            result.notifier_name,
            {"configured": True, "enabled": True, "failure_count": 0, "last_test_result": None},
        )
        state["health"] = "ok" if result.success else "error"
        if result.success:
            increment(funnel, "notifications_succeeded")
            state["last_success_time"] = utc_now()
            state["last_error_message"] = None
            state["last_error_category"] = None
            self._log(f"Alert sent via {result.notifier_name}: {alert.title}")
        else:
            increment(funnel, "notifications_failed")
            reject(funnel, "notification_failed")
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["last_failure_time"] = utc_now()
            state["last_error_message"] = result.error_message
            state["last_error_category"] = result.error_category or "unknown_error"
            logger.error("Notification failed via %s: %s", result.notifier_name, result.error_message)
            self._log(f"Notification failed via {result.notifier_name}: {result.error_message}")
        self.store.record_notification(alert.id, result.notifier_name, result.success, result.error_message)
        self._publish(
            {
                "type": "notification_result",
                "notifier": result.notifier_name,
                "ok": result.success,
                "error": result.error_message,
            }
        )

    def _refresh_notifier_health(self, notifiers: list[Notifier], config: AppConfig) -> None:
        self.status.notifier_health = {}
        self.status.notifier_states = self._configured_notifier_states(config)
        for notifier in notifiers:
            health = notifier.health_check() if hasattr(notifier, "health_check") else None
            if health:
                self.status.notifier_health[health.notifier_name] = (
                    "ok" if health.success else f"error: {health.error_message}"
                )
                state = self.status.notifier_states.setdefault(
                    health.notifier_name,
                    {"configured": True, "enabled": True, "failure_count": 0, "last_test_result": None},
                )
                state["health"] = "ok" if health.success else "error"
                state["last_error_message"] = health.error_message
                state["last_error_category"] = health.error_category
                if health.success:
                    state["last_success_time"] = utc_now()
                else:
                    state["last_failure_time"] = utc_now()
        self.status.last_service_check_time = utc_now()

    def _ordered_notifiers(self, notifiers: list[Notifier], fallback_order: list[str]) -> list[Notifier]:
        by_key = {_canonical_notifier_key(notifier): notifier for notifier in notifiers}
        ordered = [by_key[key] for key in fallback_order if key in by_key]
        ordered_keys = {_canonical_notifier_key(notifier) for notifier in ordered}
        ordered.extend(notifier for notifier in notifiers if _canonical_notifier_key(notifier) not in ordered_keys)
        return ordered

    def _configured_notifier_states(self, config: AppConfig) -> dict[str, dict]:
        return {
            "Email": {
                "configured": bool(config.notifiers.email.to_addrs),
                "enabled": config.notifiers.email.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
            "Telegram": {
                "configured": True,
                "enabled": config.notifiers.telegram.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
            "WeCom": {
                "configured": True,
                "enabled": config.notifiers.wecom.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
            "WeChat Relay": {
                "configured": True,
                "enabled": config.notifiers.wechat.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
            "QQ Relay": {
                "configured": True,
                "enabled": config.notifiers.qq.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
            "Generic Webhook": {
                "configured": True,
                "enabled": config.notifiers.generic_webhook.enabled,
                "failure_count": 0,
                "last_test_result": None,
            },
        }

    def _log(self, message: str) -> None:
        logger.info(message)
        self.status.recent_logs.insert(0, message)
        self.status.recent_logs = self.status.recent_logs[:200]
        if self.log_callback:
            self.log_callback(message)

    def _emit_status(self) -> None:
        if self.status_callback:
            self.status_callback(self.status)

    def _publish(self, event: dict) -> None:
        if not self.event_callback:
            return
        self.status.live_event_count += 1
        self.event_callback(event)


def build_sources(config: AppConfig) -> list[NewsSource]:
    timeout = config.fetching.per_source_timeout_seconds
    sources: list[NewsSource] = []
    if config.sources.gdelt.enabled:
        sources.append(GdeltSource(timeout))
    if config.sources.google_news_rss.enabled:
        sources.append(GoogleNewsRssSource(timeout))
    if config.sources.yahoo_finance_rss.enabled:
        sources.append(YahooFinanceRssSource(timeout))
    if config.sources.public_rss.enabled:
        sources.append(PublicRssSource(config.sources.public_rss.urls, timeout))
    if config.sources.official_rss.enabled:
        sources.append(OfficialRssSource(config.sources.official_rss.urls, timeout))
    for library_source in enabled_library_sources(config.sources):
        sources.append(CustomRssSource(library_source, timeout))
    for custom_source in config.sources.custom_sources:
        if custom_source.enabled:
            sources.append(CustomRssSource(custom_source, timeout))
    return sources


def _source_cache_key(source_name: str, topic_name: str) -> str:
    return f"{source_name}::{topic_name}"


def _parse_status_time(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        from src.utils.time_utils import parse_datetime

        return parse_datetime(value)
    except Exception:  # noqa: BLE001 - status data must not break monitoring
        return None


def _cache_summary(source_states: dict[str, dict]) -> dict[str, int]:
    counts = {"cache_hit": 0, "last_known_good": 0, "updated": 0, "sources_with_cached_data": 0}
    for state in source_states.values():
        status = state.get("cache_status")
        if status in counts:
            counts[status] += 1
        if int(state.get("cached_article_count") or 0) > 0:
            counts["sources_with_cached_data"] += 1
    return counts


def _backoff_summary(source_states: dict[str, dict]) -> dict[str, int]:
    active = [state for state in source_states.values() if state.get("backoff_active")]
    return {
        "active_sources": len(active),
        "max_backoff_seconds": max([int(state.get("current_backoff_seconds") or 0) for state in active] or [0]),
    }


def build_notifiers(settings: NotifierSettings, timeout_seconds: int = 20) -> list[Notifier]:
    notifiers: list[Notifier] = []
    if settings.email.enabled:
        notifiers.append(EmailNotifier(settings.email))
    if settings.wecom.enabled:
        notifiers.append(WeComNotifier(settings.wecom, timeout_seconds))
    if settings.telegram.enabled:
        notifiers.append(TelegramNotifier(settings.telegram, timeout_seconds))
    if settings.generic_webhook.enabled:
        notifiers.append(GenericWebhookNotifier(settings.generic_webhook, timeout_seconds))
    if settings.wechat.enabled:
        notifiers.append(RelayWebhookNotifier(settings.wechat, timeout_seconds))
    if settings.qq.enabled:
        notifiers.append(RelayWebhookNotifier(settings.qq, timeout_seconds))
    return notifiers


def _canonical_notifier_key(notifier: Notifier) -> str:
    name = getattr(notifier, "name", "").casefold()
    if "email" in name:
        return "email"
    if "telegram" in name:
        return "telegram"
    if "wecom" in name:
        return "wecom"
    if "wechat" in name:
        return "wechat_relay"
    if "qq" in name:
        return "qq_relay"
    if "webhook" in name:
        return "generic_webhook"
    return name.replace(" ", "_")


def _classify_source_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPError):
        return classify_feed_http_error(exc)
    text = str(exc)
    for category in (
        "api_rate_limited",
        "api_bad_response",
        "api_timeout",
        "query_too_long",
        "unsupported_query_shape",
        "invalid_encoded_query",
        "feed_parse_failed",
    ):
        if text.startswith(f"{category}:"):
            return category
    if "timed out" in text.casefold() or "timeout" in text.casefold():
        return "api_timeout"
    return "unknown_error"


class E2ETestSource(NewsSource):
    name = "E2E Test Source"

    def __init__(self, run_id: str):
        self.run_id = run_id

    def fetch(self, topic: TopicConfig) -> list[Article]:
        return [
            Article(
                title="[E2E TEST] OpenAI announces new AI infrastructure partnership with NVIDIA",
                url=f"https://example.test/e2e-openai-nvidia?run={self.run_id}",
                source=self.name,
                published_at=utc_now(),
                snippet="A controlled test article used to verify the monitoring pipeline.",
                language="en",
                raw={"test_mode": True, "run_id": self.run_id},
                reliability_score=0.9,
                ownership="AI News Monitor",
                bias_hint="Controlled local fixture; not real news.",
                category="Semiconductor/AI",
                source_type="test_fixture",
                source_tier=1,
                source_role="official",
                editorial_context="Test-only fixture for E2E pipeline verification.",
            )
        ]


class E2ETestLlmClient:
    api_key = "test-mode"

    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        return LLMAnalysis(
            relevance_score=95,
            is_actionable_alert=True,
            event_type="e2e_test",
            summary="Controlled E2E test analysis. This is not real news.",
            why_it_matters="It proves the fetch, candidate, LLM, alert, and notification pipeline can complete.",
            market_watch_suggestions=[
                MarketWatchSuggestion(
                    ticker="TEST",
                    name_or_theme="E2E pipeline",
                    possible_direction="unclear",
                    reason="This is a test-only notification with no market meaning.",
                    confidence="low",
                )
            ],
            bullish_path="Not applicable; this is a controlled test.",
            bearish_path="Not applicable; this is a controlled test.",
            risk_notes="This test alert must not be treated as real news or financial advice.",
            uncertainty_notes="The source and analysis are deterministic test fixtures.",
            source_reliability="low",
            recommended_user_action="watch_only",
            notification_title="[E2E TEST] AI News Monitor pipeline verified",
        )


def _source_error_summary(source_name: str, category: str, exc: Exception) -> str:
    if category == "api_rate_limited":
        return f"{source_name}: rate limited"
    if category == "api_timeout":
        return f"{source_name}: request timed out"
    if category == "feed_parse_failed":
        return f"{source_name}: response parse failed"
    if category == "tls_or_certificate_error":
        return f"{source_name}: TLS or certificate error"
    if category == "network_unreachable":
        return f"{source_name}: network unreachable"
    if category == "proxy_or_firewall_issue":
        return f"{source_name}: proxy or firewall issue"
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else category
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    return f"{source_name}: {category} ({text})"
