from __future__ import annotations

import os
import shutil
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import yaml

from src.models import (
    AlertSettings,
    AppConfig,
    AppSettings,
    BiasSettings,
    CustomNewsSourceConfig,
    EmailSettings,
    EnrichmentSettings,
    FetchingSettings,
    GenericWebhookSettings,
    IntelligenceGapSettings,
    LLMProviderSettings,
    LLMSettings,
    LocalServerSettings,
    MonitorSettings,
    NotificationRoutingSettings,
    NotifierSettings,
    OfficialRssSettings,
    QualitySettings,
    RelayWebhookSettings,
    SmartPollingSettings,
    SocialSourcesSettings,
    SourceCacheSettings,
    SourceHealthSettings,
    SourceLibraryItem,
    SourceSettings,
    SourceToggle,
    TelegramSettings,
    TopicConfig,
    UiSettings,
    WebhookSettings,
    XCostGuardSettings,
    XSourceSettings,
)
from src.secrets import load_env_file
from src.sources.library import default_source_library, merge_source_library
from src.utils.url_utils import is_valid_http_url

APP_NAME = "AI News Monitor"
CONFIG_FILENAMES = ("config.yaml", "user_config.yaml")
RECOMMENDED_LLM_DEFAULTS = {
    "temperature": 0.7,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "max_tokens": 1024,
    "timeout_seconds": 30,
}
RECOMMENDED_EMAIL_DEFAULTS = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": True,
}
PUBLIC_RSS_DEFAULTS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "https://export.arxiv.org/rss/cs.AI",
]
SOURCE_ROLES = {"official", "wire", "major_media", "niche_media", "company_ir", "aggregator", "blog", "custom"}
PROPAGANDA_RISKS = {"low", "medium", "high", "unknown"}
SOURCE_MODES = {"manual", "auto", "hybrid"}
KNOWN_TOPIC_DOMAINS = {
    "technology",
    "ai_industry",
    "finance",
    "public_companies",
    "politics",
    "elections",
    "geopolitics",
    "history",
    "science",
    "health",
    "culture",
    "general_breaking_news",
    "public_policy",
    "local_news",
    "semiconductor",
    "custom",
}
OPENAI_COMPATIBLE_PROVIDERS = {"openai_compatible", "openai", "deepseek"}


class ConfigError(ValueError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def bundled_resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", executable_dir()))
    return project_root()


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def resolve_runtime_dir() -> Path:
    exe_dir = executable_dir()
    if any((exe_dir / name).exists() for name in CONFIG_FILENAMES) or (exe_dir / ".env").exists():
        return exe_dir
    return app_data_dir()


def ensure_runtime_files(runtime_dir: Path | None = None) -> Path:
    runtime_dir = runtime_dir or resolve_runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    root = bundled_resource_dir()
    config_path = runtime_dir / "config.yaml"
    env_path = runtime_dir / ".env"
    if not config_path.exists():
        example = root / "config.example.yaml"
        if example.exists():
            shutil.copyfile(example, config_path)
        else:
            save_config(AppConfig(), config_path)
    if not env_path.exists():
        example = root / ".env.example"
        if example.exists():
            shutil.copyfile(example, env_path)
        else:
            env_path.write_text("", encoding="utf-8")
    return runtime_dir


def load_config(path: Path | None = None, load_env: bool = True) -> AppConfig:
    runtime_dir = path.parent if path else ensure_runtime_files()
    config_path = path or runtime_dir / "config.yaml"
    if load_env:
        load_env_file(runtime_dir / ".env")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = parse_config(data)
    validate_config(config)
    return config


def save_config(config: AppConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config_to_dict(config), sort_keys=False, allow_unicode=True), encoding="utf-8")


def parse_config(data: dict[str, Any]) -> AppConfig:
    app = _parse_app(data.get("app", {}))
    return AppConfig(
        app=app,
        monitor=_parse_monitor(data.get("monitor", {})),
        llm=_parse_llm(data.get("llm", {})),
        alerts=_parse_alerts(data.get("alerts", {})),
        quality=_parse_quality(data.get("quality", {})),
        notifications=_parse_notifications(data.get("notifications", {})),
        sources=_parse_sources(data.get("sources", {})),
        social_sources=_parse_social_sources(data.get("social_sources", {})),
        source_health=_parse_source_health(data.get("source_health", {})),
        source_cache=_parse_source_cache(data.get("source_cache", {})),
        smart_polling=_parse_smart_polling(data.get("smart_polling", {})),
        fetching=_parse_fetching(data.get("fetching", {})),
        intelligence_gaps=_parse_intelligence_gaps(data.get("intelligence_gaps", {})),
        enrichment=_parse_enrichment(data.get("enrichment", {}), app.output_language),
        bias=_parse_bias(data.get("bias", {})),
        local_server=_parse_local_server(data.get("local_server", {})),
        ui=_parse_ui(data.get("ui", {})),
        notifiers=_parse_notifiers(data.get("notifiers", {})),
        topics=[_parse_topic(item) for item in data.get("topics", []) or []],
    )


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    data = asdict(config)
    if config.llm.preset == "recommended":
        for key in RECOMMENDED_LLM_DEFAULTS:
            data["llm"].pop(key, None)
    if config.notifiers.email.preset == "recommended":
        for key in RECOMMENDED_EMAIL_DEFAULTS:
            data["notifiers"]["email"].pop(key, None)
    if config.notifiers.generic_webhook.preset == "recommended":
        generic = data["notifiers"]["generic_webhook"]
        if generic.get("method") == "POST":
            generic.pop("method", None)
        if not generic.get("headers"):
            generic.pop("headers", None)
        if generic.get("body_template") == "default":
            generic.pop("body_template", None)
    return data


def validate_config(config: AppConfig) -> None:
    if config.monitor.default_interval_seconds < 15:
        raise ConfigError("Default poll interval must be at least 15 seconds.")
    if not 0 <= config.monitor.min_relevance_score <= 100:
        raise ConfigError("Default relevance threshold must be between 0 and 100.")
    if config.monitor.max_alerts_per_hour < 1:
        raise ConfigError("Max alerts per hour must be at least 1.")
    if config.llm.timeout_seconds <= 0 or config.llm.max_tokens <= 0:
        raise ConfigError("LLM timeout and max tokens must be positive.")
    if config.llm.preset not in {"recommended", "custom"}:
        raise ConfigError("LLM preset must be recommended or custom.")
    if config.llm.provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise ConfigError("LLM provider must be openai_compatible, openai, or deepseek.")
    if not 0 <= config.llm.temperature <= 2:
        raise ConfigError("LLM temperature must be between 0 and 2.")
    if not 0 <= config.llm.top_p <= 1:
        raise ConfigError("LLM top_p must be between 0 and 1.")
    if not -2 <= config.llm.presence_penalty <= 2:
        raise ConfigError("LLM presence_penalty must be between -2 and 2.")
    if not is_valid_http_url(config.llm.base_url):
        raise ConfigError("LLM base URL must be a valid HTTP or HTTPS URL.")
    for provider_name in config.llm.fallback_providers:
        if provider_name not in config.llm.providers and provider_name not in OPENAI_COMPATIBLE_PROVIDERS:
            raise ConfigError(f"Unknown LLM fallback provider: {provider_name}")
    for name, provider in config.llm.providers.items():
        validate_llm_provider(name, provider)
    validate_language(config.app.output_language, "App output language")
    validate_enrichment(config.enrichment)
    validate_bias(config.bias)
    validate_local_server(config.local_server)
    validate_alerts(config.alerts)
    validate_quality(config.quality)
    validate_notifications(config.notifications)
    validate_sources(config.sources)
    validate_social_sources(config.social_sources)
    validate_source_health(config.source_health)
    validate_source_cache(config.source_cache)
    validate_smart_polling(config.smart_polling)
    validate_fetching(config.fetching)
    validate_intelligence_gaps(config.intelligence_gaps)
    for topic in config.topics:
        validate_topic(topic)


def validate_sources(sources: SourceSettings) -> None:
    for url in sources.public_rss.urls:
        if not is_valid_http_url(url):
            raise ConfigError(f"Public RSS URL is invalid: {url}")
    for url in sources.official_rss.urls:
        if not is_valid_http_url(url):
            raise ConfigError(f"Official RSS URL is invalid: {url}")
    seen_names: set[str] = set()
    seen_urls: set[str] = set()
    for source in sources.custom_sources:
        if not source.name.strip():
            raise ConfigError("Custom news source name is required.")
        if source.kind != "rss":
            raise ConfigError(f"Unsupported custom news source type: {source.kind}")
        if not is_valid_http_url(source.url):
            raise ConfigError(f"Custom news source URL is invalid: {source.url}")
        if not 0 <= source.reliability_score <= 1:
            raise ConfigError(f"Custom news source reliability must be between 0 and 1: {source.name}")
        validate_source_metadata(source.source_tier, source.source_role, source.propaganda_risk, source.name)
        if source.default_language:
            validate_language(source.default_language, f"Custom source language for {source.name}")
        if source.website_url and not is_valid_http_url(source.website_url):
            raise ConfigError(f"Custom news source website URL is invalid: {source.website_url}")
        if source.help_url and not is_valid_http_url(source.help_url):
            raise ConfigError(f"Custom news source help URL is invalid: {source.help_url}")
        name_key = source.name.strip().casefold()
        url_key = source.url.strip().casefold()
        if name_key in seen_names:
            raise ConfigError(f"Duplicate custom news source name: {source.name}")
        if url_key in seen_urls:
            raise ConfigError(f"Duplicate custom news source URL: {source.url}")
        seen_names.add(name_key)
        seen_urls.add(url_key)
    library_ids: set[str] = set()
    for source in sources.library:
        if not source.id.strip():
            raise ConfigError("Source library item id is required.")
        if source.id in library_ids:
            raise ConfigError(f"Duplicate source library item id: {source.id}")
        if not source.name.strip():
            raise ConfigError("Source library item name is required.")
        if source.kind not in {"rss", "website", "api"}:
            raise ConfigError(f"Unsupported source library type: {source.kind}")
        if not is_valid_http_url(source.url):
            raise ConfigError(f"Source library URL is invalid: {source.url}")
        if source.language:
            validate_language(source.language, f"Source library language for {source.name}")
        if not 0 <= source.reliability_score <= 1:
            raise ConfigError(f"Source library reliability must be between 0 and 1: {source.name}")
        validate_source_metadata(source.source_tier, source.source_role, source.propaganda_risk, source.name)
        if source.website_url and not is_valid_http_url(source.website_url):
            raise ConfigError(f"Source library website URL is invalid: {source.website_url}")
        if source.help_url and not is_valid_http_url(source.help_url):
            raise ConfigError(f"Source library help URL is invalid: {source.help_url}")
        library_ids.add(source.id)


def validate_social_sources(settings: SocialSourcesSettings) -> None:
    x = settings.x
    if x.enabled and not x.bearer_token_env.strip():
        raise ConfigError("X.com source requires bearer_token_env when enabled.")
    if x.max_posts_per_topic_per_run < 1:
        raise ConfigError("X.com max_posts_per_topic_per_run must be positive.")
    if not 1 <= x.search_recent_days_limit <= 7:
        raise ConfigError("X.com search_recent_days_limit must be between 1 and 7.")
    if x.min_author_followers is not None and x.min_author_followers < 0:
        raise ConfigError("X.com min_author_followers cannot be negative.")
    if x.cost_guard.daily_max_read_posts < 1:
        raise ConfigError("X.com daily_max_read_posts must be positive.")
    if not 1 <= x.cost_guard.warn_when_reaching_percent <= 100:
        raise ConfigError("X.com warn_when_reaching_percent must be between 1 and 100.")


def validate_alerts(settings: AlertSettings) -> None:
    if settings.default_mode not in {"fast", "full_analysis"}:
        raise ConfigError("Alert default_mode must be fast or full_analysis.")


def validate_quality(settings: QualitySettings) -> None:
    for field_name in (
        "official_source_boost",
        "company_ir_boost",
        "multi_source_confirmation_boost",
        "independent_source_bonus",
        "same_owner_confirmation_penalty",
        "low_quality_source_penalty",
        "duplicate_rewrite_penalty",
        "event_cluster_strength_boost",
        "whitelist_boost",
    ):
        value = getattr(settings, field_name)
        if not 0 <= value <= 1:
            raise ConfigError(f"Quality {field_name} must be between 0 and 1.")
    for category, priority in settings.category_priority.items():
        if not category.strip():
            raise ConfigError("Quality category priority name cannot be empty.")
        if not -1 <= priority <= 1:
            raise ConfigError(f"Quality category priority must be between -1 and 1: {category}")


def validate_source_metadata(source_tier: int, source_role: str, propaganda_risk: str, name: str) -> None:
    if int(source_tier) not in {1, 2, 3, 4}:
        raise ConfigError(f"Source tier must be 1, 2, 3, or 4: {name}")
    if source_role not in SOURCE_ROLES:
        raise ConfigError(f"Unknown source role for {name}: {source_role}")
    if propaganda_risk not in PROPAGANDA_RISKS:
        raise ConfigError(f"Unknown propaganda risk for {name}: {propaganda_risk}")


def validate_source_health(settings: SourceHealthSettings) -> None:
    if settings.fresh_within_minutes < 1:
        raise ConfigError("source_health.fresh_within_minutes must be positive.")
    if settings.stale_after_minutes < settings.fresh_within_minutes:
        raise ConfigError("source_health.stale_after_minutes must be >= fresh_within_minutes.")
    if settings.very_stale_after_minutes < settings.stale_after_minutes:
        raise ConfigError("source_health.very_stale_after_minutes must be >= stale_after_minutes.")
    if settings.max_consecutive_failures_before_degraded < 1:
        raise ConfigError("source_health.max_consecutive_failures_before_degraded must be at least 1.")


def validate_source_cache(settings: SourceCacheSettings) -> None:
    if settings.source_ttl_seconds < 0 or settings.digest_ttl_seconds < 0:
        raise ConfigError("source_cache TTL values cannot be negative.")
    if settings.last_known_good_max_age_hours < 1:
        raise ConfigError("source_cache.last_known_good_max_age_hours must be at least 1.")


def validate_smart_polling(settings: SmartPollingSettings) -> None:
    if settings.failure_backoff_multiplier < 1:
        raise ConfigError("smart_polling.failure_backoff_multiplier must be at least 1.")
    if settings.max_backoff_minutes < 1:
        raise ConfigError("smart_polling.max_backoff_minutes must be at least 1.")


def validate_fetching(settings: FetchingSettings) -> None:
    if settings.per_source_timeout_seconds < 1:
        raise ConfigError("fetching.per_source_timeout_seconds must be positive.")
    if settings.overall_cycle_deadline_seconds < settings.per_source_timeout_seconds:
        raise ConfigError("fetching.overall_cycle_deadline_seconds must be >= per_source_timeout_seconds.")
    if settings.max_articles_per_source < 1 or settings.max_candidate_articles_per_topic < 1:
        raise ConfigError("fetching article limits must be positive.")


def validate_intelligence_gaps(settings: IntelligenceGapSettings) -> None:
    if settings.critical_gap_cooldown_minutes < 1:
        raise ConfigError("intelligence_gaps.critical_gap_cooldown_minutes must be at least 1.")


def validate_notifications(settings: NotificationRoutingSettings) -> None:
    allowed = {"email", "telegram", "wecom", "wechat_relay", "qq_relay", "generic_webhook"}
    for channel in settings.fallback_order:
        if channel not in allowed:
            raise ConfigError(f"Unknown notification fallback channel: {channel}")
    if settings.retry_attempts < 1:
        raise ConfigError("Notification retry_attempts must be at least 1.")
    if settings.retry_base_delay_seconds < 0:
        raise ConfigError("Notification retry_base_delay_seconds cannot be negative.")


def validate_enrichment(settings: EnrichmentSettings) -> None:
    validate_language(settings.target_language, "Translation target language")
    if not settings.allowed_languages:
        raise ConfigError("At least one allowed language is required.")
    for language in settings.allowed_languages:
        validate_language(language, "Allowed language")


def validate_bias(settings: BiasSettings) -> None:
    if settings.mode not in {"single", "cluster"}:
        raise ConfigError("Bias mode must be single or cluster.")
    if settings.min_cluster_size < 1:
        raise ConfigError("Bias min_cluster_size must be at least 1.")


def validate_local_server(settings: LocalServerSettings) -> None:
    if not 1024 <= settings.port <= 65535:
        raise ConfigError("Local server port must be between 1024 and 65535.")
    if settings.allow_lan and settings.host not in {"0.0.0.0", "::"}:
        raise ConfigError("LAN sharing requires local_server.host to be 0.0.0.0 or ::.")


def validate_language(value: str, field_name: str) -> None:
    if value not in {"zh-CN", "en"}:
        raise ConfigError(f"{field_name} must be zh-CN or en.")


def validate_topic(topic: TopicConfig) -> None:
    if not topic.name.strip():
        raise ConfigError("Topic name is required.")
    if not topic.prompt.strip():
        raise ConfigError(f"Topic '{topic.name}' requires a prompt.")
    if not topic.broad_search and not [keyword for keyword in topic.keywords if keyword.strip()]:
        raise ConfigError(f"Topic '{topic.name}' needs at least one keyword or broad search mode.")
    if topic.source_mode not in SOURCE_MODES:
        raise ConfigError(f"Topic '{topic.name}' source_mode must be manual, auto, or hybrid.")
    if not 0 <= int(topic.min_relevance_score) <= 100:
        raise ConfigError(f"Topic '{topic.name}' threshold must be between 0 and 100.")
    if not 0 <= float(topic.min_confidence_score) <= 1:
        raise ConfigError(f"Topic '{topic.name}' confidence threshold must be between 0 and 1.")
    validate_language(topic.output_language, f"Topic '{topic.name}' output language")
    for domain in topic.domains:
        normalized = domain.strip().casefold().replace("-", "_").replace(" ", "_")
        if normalized and normalized not in KNOWN_TOPIC_DOMAINS:
            raise ConfigError(f"Topic '{topic.name}' has an unknown domain: {domain}")
    if topic.poll_interval_seconds is not None and topic.poll_interval_seconds < 15:
        raise ConfigError(f"Topic '{topic.name}' poll interval must be at least 15 seconds.")
    if topic.cooldown_minutes is not None and topic.cooldown_minutes < 0:
        raise ConfigError(f"Topic '{topic.name}' cooldown cannot be negative.")
    for url in topic.official_rss_urls:
        if not is_valid_http_url(url):
            raise ConfigError(f"Topic '{topic.name}' has an invalid RSS URL: {url}")


def _parse_app(data: dict[str, Any]) -> AppSettings:
    return AppSettings(
        output_language=str(data.get("output_language", "zh-CN")),
        portable_mode=bool(data.get("portable_mode", True)),
        run_minimized_to_tray=bool(data.get("run_minimized_to_tray", False)),
    )


def _parse_monitor(data: dict[str, Any]) -> MonitorSettings:
    return MonitorSettings(
        default_interval_seconds=int(data.get("default_interval_seconds", 600)),
        min_relevance_score=int(data.get("min_relevance_score", 80)),
        max_alerts_per_hour=int(data.get("max_alerts_per_hour", 5)),
        deduplicate_hours=int(data.get("deduplicate_hours", 72)),
        request_timeout_seconds=int(data.get("request_timeout_seconds", 20)),
        log_retention_days=int(data.get("log_retention_days", 14)),
    )


def _parse_llm(data: dict[str, Any]) -> LLMSettings:
    preset = str(data.get("preset", "recommended"))
    defaults = RECOMMENDED_LLM_DEFAULTS if preset == "recommended" else {}
    providers = {
        str(name): _parse_llm_provider(str(name), item or {})
        for name, item in (data.get("providers", {}) or {}).items()
    }
    provider_name = str(data.get("provider", "openai_compatible"))
    resolved_provider = _resolve_llm_provider(provider_name, providers)
    return LLMSettings(
        preset=preset,
        provider=provider_name,
        fallback_providers=[str(item) for item in data.get("fallback_providers", []) or []],
        base_url=str(data.get("base_url", resolved_provider.base_url)),
        model=str(data.get("model", resolved_provider.model)),
        api_key_env=str(data.get("api_key_env", resolved_provider.api_key_env)),
        providers=providers,
        structured_outputs=bool(data.get("structured_outputs", resolved_provider.structured_outputs)),
        temperature=float(data.get("temperature", defaults.get("temperature", 0.7))),
        top_p=float(data.get("top_p", defaults.get("top_p", 1.0))),
        presence_penalty=float(data.get("presence_penalty", defaults.get("presence_penalty", 0.0))),
        max_tokens=int(data.get("max_tokens", defaults.get("max_tokens", 1024))),
        timeout_seconds=int(data.get("timeout_seconds", resolved_provider.timeout_seconds)),
        max_retries=int(data.get("max_retries", resolved_provider.max_retries)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", resolved_provider.retry_backoff_seconds)),
    )


def _parse_llm_provider(name: str, data: dict[str, Any]) -> LLMProviderSettings:
    defaults = _default_llm_provider(name)
    thinking = data.get("thinking", {}) or {}
    return LLMProviderSettings(
        enabled=bool(data.get("enabled", defaults.enabled)),
        api_key_env=str(data.get("api_key_env", defaults.api_key_env)),
        base_url=str(data.get("base_url", defaults.base_url)),
        model=str(data.get("model", defaults.model)),
        timeout_seconds=int(data.get("timeout_seconds", defaults.timeout_seconds)),
        max_retries=int(data.get("max_retries", defaults.max_retries)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", defaults.retry_backoff_seconds)),
        structured_outputs=bool(data.get("structured_outputs", defaults.structured_outputs)),
        thinking_enabled=bool(thinking.get("enabled", defaults.thinking_enabled)),
        reasoning_effort=str(thinking.get("reasoning_effort", defaults.reasoning_effort)),
    )


def _default_llm_provider(name: str) -> LLMProviderSettings:
    if name == "deepseek":
        return LLMProviderSettings(
            enabled=False,
            api_key_env="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            timeout_seconds=60,
            max_retries=3,
            retry_backoff_seconds=2.0,
            structured_outputs=True,
        )
    if name == "openai":
        return LLMProviderSettings(
            enabled=True,
            api_key_env="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            model="gpt-4.1-mini",
        )
    return LLMProviderSettings()


def _resolve_llm_provider(name: str, providers: dict[str, LLMProviderSettings]) -> LLMProviderSettings:
    if name in providers:
        return providers[name]
    if name in {"openai", "deepseek"}:
        return _default_llm_provider(name)
    return _default_llm_provider("openai_compatible")


def validate_llm_provider(name: str, provider: LLMProviderSettings) -> None:
    if name not in OPENAI_COMPATIBLE_PROVIDERS:
        raise ConfigError(f"Unknown LLM provider configuration: {name}")
    if provider.enabled and not provider.api_key_env.strip():
        raise ConfigError(f"LLM provider {name} requires api_key_env when enabled.")
    if not is_valid_http_url(provider.base_url):
        raise ConfigError(f"LLM provider {name} base_url must be a valid HTTP or HTTPS URL.")
    if not provider.model.strip():
        raise ConfigError(f"LLM provider {name} model is required.")
    if provider.timeout_seconds <= 0:
        raise ConfigError(f"LLM provider {name} timeout_seconds must be positive.")
    if provider.max_retries < 0:
        raise ConfigError(f"LLM provider {name} max_retries cannot be negative.")
    if provider.retry_backoff_seconds < 0:
        raise ConfigError(f"LLM provider {name} retry_backoff_seconds cannot be negative.")


def _parse_alerts(data: dict[str, Any]) -> AlertSettings:
    return AlertSettings(default_mode=str(data.get("default_mode", "fast")))  # type: ignore[arg-type]


def _parse_quality(data: dict[str, Any]) -> QualitySettings:
    return QualitySettings(
        official_source_boost=float(data.get("official_source_boost", 0.10)),
        company_ir_boost=float(data.get("company_ir_boost", 0.10)),
        multi_source_confirmation_boost=float(data.get("multi_source_confirmation_boost", 0.15)),
        independent_source_bonus=float(data.get("independent_source_bonus", 0.05)),
        same_owner_confirmation_penalty=float(data.get("same_owner_confirmation_penalty", 0.05)),
        low_quality_source_penalty=float(data.get("low_quality_source_penalty", 0.20)),
        duplicate_rewrite_penalty=float(data.get("duplicate_rewrite_penalty", 0.10)),
        event_cluster_strength_boost=float(data.get("event_cluster_strength_boost", 0.05)),
        whitelist_boost=float(data.get("whitelist_boost", 0.20)),
        blacklist_exclude=bool(data.get("blacklist_exclude", True)),
        whitelist_sources=[str(item) for item in data.get("whitelist_sources", []) or []],
        blacklist_sources=[str(item) for item in data.get("blacklist_sources", []) or []],
        category_priority={str(k): float(v) for k, v in (data.get("category_priority", {}) or {}).items()},
    )


def _parse_notifications(data: dict[str, Any]) -> NotificationRoutingSettings:
    return NotificationRoutingSettings(
        fallback_enabled=bool(data.get("fallback_enabled", True)),
        fallback_order=[
            str(item) for item in data.get("fallback_order", NotificationRoutingSettings().fallback_order) or []
        ],
        retry_attempts=int(data.get("retry_attempts", 2)),
        retry_base_delay_seconds=float(data.get("retry_base_delay_seconds", 0.5)),
    )


def _parse_sources(data: dict[str, Any]) -> SourceSettings:
    official = data.get("official_rss", {}) or {}
    public = data.get("public_rss", {}) or {}
    configured_library = [_parse_source_library_item(item) for item in data.get("library", []) or []]
    library = (
        merge_source_library(configured_library)
        if configured_library
        else [replace(item, enabled=False) for item in default_source_library()]
    )
    return SourceSettings(
        gdelt=SourceToggle(bool((data.get("gdelt", {}) or {}).get("enabled", True))),
        google_news_rss=SourceToggle(bool((data.get("google_news_rss", {}) or {}).get("enabled", True))),
        yahoo_finance_rss=SourceToggle(bool((data.get("yahoo_finance_rss", {}) or {}).get("enabled", False))),
        public_rss=OfficialRssSettings(
            bool(public.get("enabled", False)),
            [str(url) for url in public.get("urls", PUBLIC_RSS_DEFAULTS) or []],
        ),
        official_rss=OfficialRssSettings(
            bool(official.get("enabled", True)),
            [str(url) for url in official.get("urls", []) or []],
        ),
        enabled_packages=[str(item) for item in data.get("enabled_packages", []) or []],
        library=library,
        custom_sources=[_parse_custom_source(item) for item in data.get("custom_sources", []) or []],
    )


def _parse_social_sources(data: dict[str, Any]) -> SocialSourcesSettings:
    x_data = data.get("x", {}) or {}
    guard_data = x_data.get("cost_guard", {}) or {}
    return SocialSourcesSettings(
        x=XSourceSettings(
            enabled=bool(x_data.get("enabled", False)),
            bearer_token_env=str(x_data.get("bearer_token_env", "X_BEARER_TOKEN")),
            max_posts_per_topic_per_run=int(x_data.get("max_posts_per_topic_per_run", 25)),
            include_retweets=bool(x_data.get("include_retweets", False)),
            min_author_followers=_optional_int(x_data.get("min_author_followers")),
            trusted_accounts=[str(item) for item in x_data.get("trusted_accounts", []) or []],
            blocked_accounts=[str(item) for item in x_data.get("blocked_accounts", []) or []],
            search_recent_days_limit=int(x_data.get("search_recent_days_limit", 7)),
            cost_guard=XCostGuardSettings(
                enabled=bool(guard_data.get("enabled", True)),
                daily_max_read_posts=int(guard_data.get("daily_max_read_posts", 500)),
                warn_when_reaching_percent=int(guard_data.get("warn_when_reaching_percent", 80)),
            ),
        )
    )


def _parse_source_health(data: dict[str, Any]) -> SourceHealthSettings:
    return SourceHealthSettings(
        fresh_within_minutes=int(data.get("fresh_within_minutes", 30)),
        stale_after_minutes=int(data.get("stale_after_minutes", 120)),
        very_stale_after_minutes=int(data.get("very_stale_after_minutes", 360)),
        max_consecutive_failures_before_degraded=int(data.get("max_consecutive_failures_before_degraded", 3)),
    )


def _parse_source_cache(data: dict[str, Any]) -> SourceCacheSettings:
    return SourceCacheSettings(
        enabled=bool(data.get("enabled", True)),
        source_ttl_seconds=int(data.get("source_ttl_seconds", 600)),
        digest_ttl_seconds=int(data.get("digest_ttl_seconds", 900)),
        last_known_good_enabled=bool(data.get("last_known_good_enabled", True)),
        last_known_good_max_age_hours=int(data.get("last_known_good_max_age_hours", 24)),
        allow_cached_alerts=bool(data.get("allow_cached_alerts", False)),
    )


def _parse_smart_polling(data: dict[str, Any]) -> SmartPollingSettings:
    return SmartPollingSettings(
        enabled=bool(data.get("enabled", True)),
        failure_backoff_multiplier=float(data.get("failure_backoff_multiplier", 2.0)),
        max_backoff_minutes=int(data.get("max_backoff_minutes", 60)),
        reset_after_success=bool(data.get("reset_after_success", True)),
    )


def _parse_fetching(data: dict[str, Any]) -> FetchingSettings:
    return FetchingSettings(
        per_source_timeout_seconds=int(data.get("per_source_timeout_seconds", 8)),
        overall_cycle_deadline_seconds=int(data.get("overall_cycle_deadline_seconds", 40)),
        max_articles_per_source=int(data.get("max_articles_per_source", 10)),
        max_candidate_articles_per_topic=int(data.get("max_candidate_articles_per_topic", 5)),
    )


def _parse_intelligence_gaps(data: dict[str, Any]) -> IntelligenceGapSettings:
    return IntelligenceGapSettings(
        enabled=bool(data.get("enabled", True)),
        notify_on_critical_gap=bool(data.get("notify_on_critical_gap", False)),
        critical_gap_cooldown_minutes=int(data.get("critical_gap_cooldown_minutes", 360)),
    )


def _parse_enrichment(data: dict[str, Any], default_target_language: str) -> EnrichmentSettings:
    return EnrichmentSettings(
        translation_enabled=bool(data.get("translation_enabled", True)),
        target_language=str(data.get("target_language", default_target_language)),
        allowed_languages=[str(item) for item in data.get("allowed_languages", ["zh-CN", "en"]) or []],
        summary_enabled=bool(data.get("summary_enabled", True)),
    )


def _parse_bias(data: dict[str, Any]) -> BiasSettings:
    return BiasSettings(
        enabled=bool(data.get("enabled", False)),
        mode=str(data.get("mode", "single")),  # type: ignore[arg-type]
        min_cluster_size=int(data.get("min_cluster_size", 2)),
    )


def _parse_local_server(data: dict[str, Any]) -> LocalServerSettings:
    allow_lan = bool(data.get("allow_lan", False))
    return LocalServerSettings(
        enabled=bool(data.get("enabled", True)),
        host=str(data.get("host", "0.0.0.0" if allow_lan else "127.0.0.1")),
        port=int(data.get("port", 8765)),
        allow_lan=allow_lan,
        sse_enabled=bool(data.get("sse_enabled", True)),
    )


def _parse_ui(data: dict[str, Any]) -> UiSettings:
    return UiSettings(debug_mode=bool(data.get("debug_mode", False)))


def _parse_notifiers(data: dict[str, Any]) -> NotifierSettings:
    email = data.get("email", {}) or {}
    wecom = data.get("wecom", {}) or {}
    telegram = data.get("telegram", {}) or {}
    generic = data.get("generic_webhook", {}) or {}
    wechat = data.get("wechat", {}) or {}
    qq = data.get("qq", {}) or {}
    return NotifierSettings(
        email=EmailSettings(
            preset=str(email.get("preset", "recommended")),
            enabled=bool(email.get("enabled", True)),
            smtp_host=str(email.get("smtp_host", RECOMMENDED_EMAIL_DEFAULTS["smtp_host"])),
            smtp_port=int(email.get("smtp_port", RECOMMENDED_EMAIL_DEFAULTS["smtp_port"])),
            use_tls=bool(email.get("use_tls", RECOMMENDED_EMAIL_DEFAULTS["use_tls"])),
            username_env=str(email.get("username_env", "EMAIL_USERNAME")),
            password_env=str(email.get("password_env", "EMAIL_APP_PASSWORD")),
            from_addr_env=str(email.get("from_addr_env", "EMAIL_FROM")),
            to_addrs=[str(addr) for addr in email.get("to_addrs", []) or []],
        ),
        wecom=WebhookSettings(
            preset=str(wecom.get("preset", "recommended")),
            enabled=bool(wecom.get("enabled", False)),
            webhook_url_env=str(wecom.get("webhook_url_env", "WECOM_WEBHOOK_URL")),
        ),
        telegram=TelegramSettings(
            preset=str(telegram.get("preset", "recommended")),
            enabled=bool(telegram.get("enabled", False)),
            bot_token_env=str(telegram.get("bot_token_env", "TELEGRAM_BOT_TOKEN")),
            chat_id_env=str(telegram.get("chat_id_env", "TELEGRAM_CHAT_ID")),
        ),
        generic_webhook=GenericWebhookSettings(
            preset=str(generic.get("preset", "recommended")),
            enabled=bool(generic.get("enabled", False)),
            url_env=str(generic.get("url_env", "GENERIC_WEBHOOK_URL")),
            method=str(generic.get("method", "POST")).upper(),
            headers={str(k): str(v) for k, v in (generic.get("headers", {}) or {}).items()},
            body_template=str(generic.get("body_template", "default")),
        ),
        wechat=_parse_relay_webhook(
            wechat,
            provider="serverchan",
            url_env="WECHAT_RELAY_WEBHOOK_URL",
            channel_name="WeChat Relay",
        ),
        qq=_parse_relay_webhook(
            qq,
            provider="qmsg",
            url_env="QQ_RELAY_WEBHOOK_URL",
            channel_name="QQ Relay",
        ),
    )


def _parse_relay_webhook(
    data: dict[str, Any],
    *,
    provider: str,
    url_env: str,
    channel_name: str,
) -> RelayWebhookSettings:
    return RelayWebhookSettings(
        preset=str(data.get("preset", "recommended")),
        enabled=bool(data.get("enabled", False)),
        provider=str(data.get("provider", provider)),
        webhook_url_env=str(data.get("webhook_url_env", url_env)),
        channel_name=str(data.get("channel_name", channel_name)),
    )


def _parse_custom_source(data: dict[str, Any]) -> CustomNewsSourceConfig:
    return CustomNewsSourceConfig(
        name=str(data.get("name", "")),
        url=str(data.get("url", "")),
        enabled=bool(data.get("enabled", True)),
        kind=str(data.get("kind", "rss")),
        category=str(data.get("category", "Custom")),
        reliability_score=float(data.get("reliability_score", 0.6)),
        source_tier=int(data.get("source_tier", 4)),
        source_role=str(data.get("source_role", "custom")),  # type: ignore[arg-type]
        state_affiliated=bool(data.get("state_affiliated", False)),
        propaganda_risk=str(data.get("propaganda_risk", "unknown")),  # type: ignore[arg-type]
        editorial_context=str(data.get("editorial_context", "")),
        ownership=str(data.get("ownership")) if data.get("ownership") is not None else None,
        bias_hint=str(data.get("bias_hint")) if data.get("bias_hint") is not None else None,
        default_language=str(data.get("default_language")) if data.get("default_language") is not None else None,
        website_url=str(data.get("website_url")) if data.get("website_url") is not None else None,
        help_url=str(data.get("help_url")) if data.get("help_url") is not None else None,
    )


def _parse_source_library_item(data: dict[str, Any]) -> SourceLibraryItem:
    category = str(data.get("category", "Global News"))
    ownership = str(data.get("ownership", ""))
    bias_hint = str(data.get("bias_hint", ""))
    source_type = str(data.get("source_type", data.get("kind", "rss")))
    defaults = _metadata_defaults(category, ownership, bias_hint, source_type)
    return SourceLibraryItem(
        id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        url=str(data.get("url", "")),
        enabled=bool(data.get("enabled", False)),
        kind=str(data.get("kind", "rss")),
        category=category,
        packages=[str(item) for item in data.get("packages", []) or []],
        language=str(data.get("language", "en")),
        reliability_score=float(data.get("reliability_score", 0.6)),
        source_tier=int(data.get("source_tier", defaults["source_tier"])),
        source_role=str(data.get("source_role", defaults["source_role"])),  # type: ignore[arg-type]
        state_affiliated=bool(data.get("state_affiliated", defaults["state_affiliated"])),
        propaganda_risk=str(data.get("propaganda_risk", defaults["propaganda_risk"])),  # type: ignore[arg-type]
        editorial_context=str(data.get("editorial_context", defaults["editorial_context"])),
        ownership=str(data.get("ownership")) if data.get("ownership") is not None else None,
        bias_hint=str(data.get("bias_hint")) if data.get("bias_hint") is not None else None,
        source_type=str(data.get("source_type", "rss")),
        website_url=str(data.get("website_url")) if data.get("website_url") is not None else None,
        help_url=str(data.get("help_url")) if data.get("help_url") is not None else None,
    )


def _metadata_defaults(category: str, ownership: str, bias_hint: str, source_type: str) -> dict[str, object]:
    text = " ".join([category, ownership, bias_hint, source_type]).casefold()
    if "official" in text or "government" in text or "ministry" in text or "department" in text:
        return {
            "source_tier": 1,
            "source_role": "official",
            "state_affiliated": True,
            "propaganda_risk": "low",
            "editorial_context": "Official or primary institutional source.",
        }
    if "company ir" in text or "company-owned" in text or "newsroom" in text:
        return {
            "source_tier": 1,
            "source_role": "company_ir",
            "state_affiliated": False,
            "propaganda_risk": "low",
            "editorial_context": "Company-owned primary source.",
        }
    if "xinhua" in text or "state media" in text:
        return {
            "source_tier": 2,
            "source_role": "major_media",
            "state_affiliated": True,
            "propaganda_risk": "medium",
            "editorial_context": "State-affiliated media; compare with independent sources.",
        }
    if "aggregator" in text or "google news" in text or "yahoo finance" in text or source_type == "api":
        return {
            "source_tier": 4,
            "source_role": "aggregator",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "editorial_context": "Aggregator or index source; verify original publisher context.",
        }
    if category in {"Global News", "Finance"}:
        return {
            "source_tier": 2,
            "source_role": "major_media",
            "state_affiliated": False,
            "propaganda_risk": "low",
            "editorial_context": "Established public news or financial media source.",
        }
    if category in {"Semiconductor/AI", "China", "Taiwan", "US"}:
        return {
            "source_tier": 3,
            "source_role": "niche_media",
            "state_affiliated": False,
            "propaganda_risk": "unknown",
            "editorial_context": "Specialist or domain-specific source.",
        }
    return {
        "source_tier": 4,
        "source_role": "custom",
        "state_affiliated": False,
        "propaganda_risk": "unknown",
        "editorial_context": "",
    }


def _parse_topic(data: dict[str, Any]) -> TopicConfig:
    prompt = str(data.get("prompt", data.get("user_prompt", "")))
    threshold = data.get("notification_threshold", {}) or {}
    report_style = data.get("report_style", {}) or {}
    relevance_score = data.get("min_relevance_score", threshold.get("min_relevance_score", 80))
    return TopicConfig(
        id=str(data.get("id")) if data.get("id") is not None else None,
        name=str(data.get("name", "")),
        enabled=bool(data.get("enabled", True)),
        output_language=str(data.get("output_language", data.get("language", "zh-CN"))),
        min_relevance_score=_parse_relevance_score(relevance_score),
        min_confidence_score=float(threshold.get("min_confidence_score", data.get("min_confidence_score", 0.0))),
        cooldown_minutes=_optional_int(data.get("cooldown_minutes")),
        poll_interval_seconds=_optional_int(data.get("poll_interval_seconds")),
        prompt=prompt,
        keywords=[str(item) for item in data.get("keywords", []) or []],
        related_stocks=[str(item) for item in data.get("related_stocks", []) or []],
        official_rss_urls=[str(item) for item in data.get("official_rss_urls", []) or []],
        broad_search=bool(data.get("broad_search", False)),
        source_mode=str(data.get("source_mode", "manual")),  # type: ignore[arg-type]
        domains=[_normalize_domain(item) for item in data.get("domains", []) or []],
        preferred_regions=[str(item) for item in data.get("preferred_regions", []) or []],
        social_enabled=bool(data.get("social_enabled", False)),
        report_include_timeline=bool(report_style.get("include_timeline", True)),
        report_include_source_comparison=bool(report_style.get("include_source_comparison", True)),
        report_include_user_action=bool(report_style.get("include_user_action", True)),
    )


def _normalize_domain(value: object) -> str:
    return str(value).strip().casefold().replace("-", "_").replace(" ", "_")


def _parse_relevance_score(value: object) -> int:
    number = float(value)
    if 0 <= number <= 1:
        return int(round(number * 100))
    return int(round(number))


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
