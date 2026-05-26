from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Direction = Literal["bullish", "bearish", "mixed", "unclear"]
Confidence = Literal["low", "medium", "high"]
UserAction = Literal["watch_only", "research_further", "urgent_review", "ignore"]
Reliability = Literal["low", "medium", "high"]
AlertMode = Literal["fast", "full_analysis"]
SourceRole = Literal["official", "wire", "major_media", "niche_media", "company_ir", "aggregator", "blog", "custom"]
PropagandaRisk = Literal["low", "medium", "high", "unknown"]
FreshnessState = Literal["fresh", "stale", "very_stale", "no_data", "error", "disabled", "unknown"]
CoverageQuality = Literal["high", "medium", "low", "critical"]


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    snippet: str | None = None
    language: str | None = None
    raw: dict[str, Any] | None = None
    reliability_score: float = 0.6
    ownership: str | None = None
    bias_hint: str | None = None
    translated_title: str | None = None
    translated_snippet: str | None = None
    short_summary: str | None = None
    event_cluster_id: str | None = None
    ranking_score: float = 0.0
    category: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_tier: int = 4
    source_role: SourceRole = "custom"
    state_affiliated: bool = False
    propaganda_risk: PropagandaRisk = "unknown"
    editorial_context: str | None = None
    is_cached: bool = False
    cache_status: str | None = None
    confirmation_summary: str | None = None
    confirmation_source_count: int = 1
    independent_source_count: int = 1
    matched_keywords: list[str] = field(default_factory=list)
    match_reason: str | None = None
    selection_reason: str | None = None


@dataclass
class TimelineItem:
    date: str
    time: str | None
    label: str
    description: str
    source_title: str
    source_url: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "time": self.time,
            "label": self.label,
            "description": self.description,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


@dataclass
class SourceLink:
    title: str
    url: str
    publisher: str
    published_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "published_at": self.published_at,
        }


@dataclass
class EventCluster:
    cluster_id: str
    title: str
    articles: list[Article]
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    earliest_published_at: datetime | None = None
    latest_published_at: datetime | None = None
    confidence: float = 0.0
    relation_reason: str = ""
    timeline: list[TimelineItem] = field(default_factory=list)

    @property
    def article_count(self) -> int:
        return len(self.articles)

    @property
    def primary_article(self) -> Article:
        return self.articles[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "title": self.title,
            "article_count": self.article_count,
            "topics": self.topics,
            "entities": self.entities,
            "earliest_published_at": self.earliest_published_at.isoformat() if self.earliest_published_at else None,
            "latest_published_at": self.latest_published_at.isoformat() if self.latest_published_at else None,
            "confidence": self.confidence,
            "relation_reason": self.relation_reason,
            "timeline": [item.to_dict() for item in self.timeline],
            "articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "snippet": article.snippet,
                    "language": article.language,
                    "reliability_score": article.reliability_score,
                    "source_role": article.source_role,
                }
                for article in self.articles
            ],
        }


@dataclass
class MarketWatchSuggestion:
    ticker: str
    name_or_theme: str
    possible_direction: Direction
    reason: str
    confidence: Confidence


@dataclass
class LLMAnalysis:
    relevance_score: int
    is_actionable_alert: bool
    event_type: str
    summary: str
    why_it_matters: str
    market_watch_suggestions: list[MarketWatchSuggestion]
    bullish_path: str
    bearish_path: str
    risk_notes: str
    uncertainty_notes: str
    source_reliability: Reliability
    recommended_user_action: UserAction
    notification_title: str
    event_title: str = ""
    event_summary: str = ""
    current_status: str = ""
    timeline: list[TimelineItem] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
    affected_entities: list[str] = field(default_factory=list)
    source_links: list[SourceLink] = field(default_factory=list)
    relation_reason: str = ""
    uncertainties: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    grouped_article_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "relevance_score": self.relevance_score,
            "is_actionable_alert": self.is_actionable_alert,
            "event_type": self.event_type,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "market_watch_suggestions": [
                {
                    "ticker": item.ticker,
                    "name_or_theme": item.name_or_theme,
                    "possible_direction": item.possible_direction,
                    "reason": item.reason,
                    "confidence": item.confidence,
                }
                for item in self.market_watch_suggestions
            ],
            "bullish_path": self.bullish_path,
            "bearish_path": self.bearish_path,
            "risk_notes": self.risk_notes,
            "uncertainty_notes": self.uncertainty_notes,
            "source_reliability": self.source_reliability,
            "recommended_user_action": self.recommended_user_action,
            "notification_title": self.notification_title,
            "event_title": self.event_title,
            "event_summary": self.event_summary,
            "current_status": self.current_status,
            "timeline": [item.to_dict() for item in self.timeline],
            "key_facts": self.key_facts,
            "affected_entities": self.affected_entities,
            "source_links": [item.to_dict() for item in self.source_links],
            "relation_reason": self.relation_reason,
            "uncertainties": self.uncertainties,
            "suggested_actions": self.suggested_actions,
            "grouped_article_count": self.grouped_article_count,
            "should_notify": self.is_actionable_alert,
        }


@dataclass
class Alert:
    topic_name: str
    article: Article
    analysis: LLMAnalysis
    sent_at: datetime
    id: int | None = None
    mode: AlertMode = "fast"
    output_language: str = "zh-CN"
    event_cluster: EventCluster | None = None

    @property
    def title(self) -> str:
        return self.analysis.event_title or self.analysis.notification_title or self.article.title

    @property
    def links(self) -> list[str]:
        links = [item.url for item in self.analysis.source_links if item.url]
        if self.event_cluster:
            links.extend(article.url for article in self.event_cluster.articles if article.url)
        links.append(self.article.url)
        return list(dict.fromkeys(link for link in links if link))


@dataclass
class NotificationResult:
    notifier_name: str
    success: bool
    error_message: str | None = None
    error_category: str | None = None
    technical_detail: str | None = None
    suggested_fix: str | None = None


@dataclass
class TopicConfig:
    name: str
    enabled: bool
    prompt: str
    keywords: list[str]
    related_stocks: list[str] = field(default_factory=list)
    output_language: str = "zh-CN"
    min_relevance_score: int = 80
    poll_interval_seconds: int | None = None
    cooldown_minutes: int | None = None
    official_rss_urls: list[str] = field(default_factory=list)
    broad_search: bool = False


@dataclass
class AppSettings:
    output_language: str = "zh-CN"
    portable_mode: bool = True
    run_minimized_to_tray: bool = False


@dataclass
class MonitorSettings:
    default_interval_seconds: int = 600
    min_relevance_score: int = 80
    max_alerts_per_hour: int = 5
    deduplicate_hours: int = 72
    request_timeout_seconds: int = 20
    log_retention_days: int = 14


@dataclass
class LLMSettings:
    preset: str = "recommended"
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    api_key_env: str = "LLM_API_KEY"
    structured_outputs: bool = True
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: int = 30


@dataclass
class AlertSettings:
    default_mode: AlertMode = "fast"


@dataclass
class QualitySettings:
    official_source_boost: float = 0.10
    company_ir_boost: float = 0.10
    multi_source_confirmation_boost: float = 0.15
    independent_source_bonus: float = 0.05
    same_owner_confirmation_penalty: float = 0.05
    low_quality_source_penalty: float = 0.20
    duplicate_rewrite_penalty: float = 0.10
    event_cluster_strength_boost: float = 0.05
    whitelist_boost: float = 0.20
    blacklist_exclude: bool = True
    whitelist_sources: list[str] = field(default_factory=list)
    blacklist_sources: list[str] = field(default_factory=list)
    category_priority: dict[str, float] = field(default_factory=dict)


@dataclass
class NotificationRoutingSettings:
    fallback_enabled: bool = True
    fallback_order: list[str] = field(
        default_factory=lambda: [
            "email",
            "telegram",
            "wecom",
            "wechat_relay",
            "qq_relay",
            "generic_webhook",
        ]
    )
    retry_attempts: int = 2
    retry_base_delay_seconds: float = 0.5


@dataclass
class SourceToggle:
    enabled: bool = True


@dataclass
class OfficialRssSettings:
    enabled: bool = True
    urls: list[str] = field(default_factory=list)


@dataclass
class CustomNewsSourceConfig:
    name: str
    url: str
    enabled: bool = True
    kind: str = "rss"
    category: str = "Custom"
    reliability_score: float = 0.6
    source_tier: int = 4
    source_role: SourceRole = "custom"
    state_affiliated: bool = False
    propaganda_risk: PropagandaRisk = "unknown"
    editorial_context: str = ""
    ownership: str | None = None
    bias_hint: str | None = None
    default_language: str | None = None
    website_url: str | None = None
    help_url: str | None = None


@dataclass
class SourceLibraryItem:
    id: str
    name: str
    url: str
    enabled: bool = False
    kind: str = "rss"
    category: str = "Global News"
    packages: list[str] = field(default_factory=list)
    language: str = "en"
    reliability_score: float = 0.6
    source_tier: int = 4
    source_role: SourceRole = "custom"
    state_affiliated: bool = False
    propaganda_risk: PropagandaRisk = "unknown"
    editorial_context: str = ""
    ownership: str | None = None
    bias_hint: str | None = None
    source_type: str = "rss"
    website_url: str | None = None
    help_url: str | None = None
    last_fetch_time: datetime | None = None
    last_success_time: datetime | None = None
    last_failure_time: datetime | None = None
    last_failure_reason: str | None = None


@dataclass
class SourceSettings:
    gdelt: SourceToggle = field(default_factory=SourceToggle)
    google_news_rss: SourceToggle = field(default_factory=SourceToggle)
    yahoo_finance_rss: SourceToggle = field(default_factory=SourceToggle)
    public_rss: OfficialRssSettings = field(default_factory=OfficialRssSettings)
    official_rss: OfficialRssSettings = field(default_factory=OfficialRssSettings)
    enabled_packages: list[str] = field(default_factory=list)
    library: list[SourceLibraryItem] = field(default_factory=list)
    custom_sources: list[CustomNewsSourceConfig] = field(default_factory=list)


@dataclass
class SourceHealthSettings:
    fresh_within_minutes: int = 30
    stale_after_minutes: int = 120
    very_stale_after_minutes: int = 360
    max_consecutive_failures_before_degraded: int = 3


@dataclass
class SourceCacheSettings:
    enabled: bool = True
    source_ttl_seconds: int = 600
    digest_ttl_seconds: int = 900
    last_known_good_enabled: bool = True
    last_known_good_max_age_hours: int = 24
    allow_cached_alerts: bool = False


@dataclass
class SmartPollingSettings:
    enabled: bool = True
    failure_backoff_multiplier: float = 2.0
    max_backoff_minutes: int = 60
    reset_after_success: bool = True


@dataclass
class FetchingSettings:
    per_source_timeout_seconds: int = 8
    overall_cycle_deadline_seconds: int = 40
    max_articles_per_source: int = 10
    max_candidate_articles_per_topic: int = 5


@dataclass
class IntelligenceGapSettings:
    enabled: bool = True
    notify_on_critical_gap: bool = False
    critical_gap_cooldown_minutes: int = 360


@dataclass
class EnrichmentSettings:
    translation_enabled: bool = True
    target_language: str = "zh-CN"
    allowed_languages: list[str] = field(default_factory=lambda: ["zh-CN", "en"])
    summary_enabled: bool = True


@dataclass
class BiasSettings:
    enabled: bool = False
    mode: Literal["single", "cluster"] = "single"
    min_cluster_size: int = 2


@dataclass
class LocalServerSettings:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    allow_lan: bool = False
    sse_enabled: bool = True


@dataclass
class EmailSettings:
    preset: str = "recommended"
    enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username_env: str = "EMAIL_USERNAME"
    password_env: str = "EMAIL_APP_PASSWORD"
    from_addr_env: str = "EMAIL_FROM"
    to_addrs: list[str] = field(default_factory=list)


@dataclass
class WebhookSettings:
    preset: str = "recommended"
    enabled: bool = False
    webhook_url_env: str = ""


@dataclass
class TelegramSettings:
    preset: str = "recommended"
    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"


@dataclass
class GenericWebhookSettings:
    preset: str = "recommended"
    enabled: bool = False
    url_env: str = "GENERIC_WEBHOOK_URL"
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    body_template: str = "default"


@dataclass
class RelayWebhookSettings:
    preset: str = "recommended"
    enabled: bool = False
    provider: str = "serverchan"
    webhook_url_env: str = ""
    channel_name: str = ""


@dataclass
class NotifierSettings:
    email: EmailSettings = field(default_factory=EmailSettings)
    wecom: WebhookSettings = field(default_factory=lambda: WebhookSettings(webhook_url_env="WECOM_WEBHOOK_URL"))
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    generic_webhook: GenericWebhookSettings = field(default_factory=GenericWebhookSettings)
    wechat: RelayWebhookSettings = field(
        default_factory=lambda: RelayWebhookSettings(
            provider="serverchan",
            webhook_url_env="WECHAT_RELAY_WEBHOOK_URL",
            channel_name="WeChat Relay",
        )
    )
    qq: RelayWebhookSettings = field(
        default_factory=lambda: RelayWebhookSettings(
            provider="qmsg",
            webhook_url_env="QQ_RELAY_WEBHOOK_URL",
            channel_name="QQ Relay",
        )
    )


@dataclass
class AppConfig:
    app: AppSettings = field(default_factory=AppSettings)
    monitor: MonitorSettings = field(default_factory=MonitorSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    alerts: AlertSettings = field(default_factory=AlertSettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    notifications: NotificationRoutingSettings = field(default_factory=NotificationRoutingSettings)
    sources: SourceSettings = field(default_factory=SourceSettings)
    source_health: SourceHealthSettings = field(default_factory=SourceHealthSettings)
    source_cache: SourceCacheSettings = field(default_factory=SourceCacheSettings)
    smart_polling: SmartPollingSettings = field(default_factory=SmartPollingSettings)
    fetching: FetchingSettings = field(default_factory=FetchingSettings)
    intelligence_gaps: IntelligenceGapSettings = field(default_factory=IntelligenceGapSettings)
    enrichment: EnrichmentSettings = field(default_factory=EnrichmentSettings)
    bias: BiasSettings = field(default_factory=BiasSettings)
    local_server: LocalServerSettings = field(default_factory=LocalServerSettings)
    notifiers: NotifierSettings = field(default_factory=NotifierSettings)
    topics: list[TopicConfig] = field(default_factory=list)


@dataclass
class RuntimeStatus:
    state: str = "Stopped"
    pause_reason: str | None = None
    next_cycle_time: datetime | None = None
    active_topics_count: int = 0
    last_fetch_time: datetime | None = None
    last_successful_source_fetch: datetime | None = None
    last_llm_analysis_time: datetime | None = None
    last_alert_sent_time: datetime | None = None
    latest_articles_fetched: int = 0
    latest_candidates: int = 0
    total_articles_processed: int = 0
    queue_length: int = 0
    notifier_health: dict[str, str] = field(default_factory=dict)
    notifier_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_health: dict[str, str] = field(default_factory=dict)
    source_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_packages_enabled: list[str] = field(default_factory=list)
    source_summary: dict[str, Any] = field(default_factory=dict)
    source_cache_summary: dict[str, Any] = field(default_factory=dict)
    source_backoff_summary: dict[str, Any] = field(default_factory=dict)
    source_tier_distribution: dict[str, int] = field(default_factory=dict)
    top_failing_sources: list[dict[str, Any]] = field(default_factory=list)
    intelligence_gaps: dict[str, Any] = field(default_factory=dict)
    coverage_quality: dict[str, Any] = field(default_factory=dict)
    pipeline_funnel: dict[str, Any] = field(default_factory=dict)
    e2e_result: dict[str, Any] = field(default_factory=dict)
    llm_health: str = "unknown"
    local_server_url: str | None = None
    output_language: str = "zh-CN"
    alert_mode: AlertMode = "fast"
    last_service_check_time: datetime | None = None
    live_event_count: int = 0
    alerts_sent_today: int = 0
    recent_matches: list[dict[str, Any]] = field(default_factory=list)
    recent_event_clusters: list[dict[str, Any]] = field(default_factory=list)
    recent_alerts: list[Alert] = field(default_factory=list)
    recent_logs: list[str] = field(default_factory=list)
    error_message: str | None = None
