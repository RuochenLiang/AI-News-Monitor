from __future__ import annotations

import os
import threading
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigError, load_config, save_config, validate_config
from src.i18n import text
from src.llm_client import LLMClient
from src.models import CustomNewsSourceConfig, LLMProviderSettings, SourceLibraryItem
from src.monitor import build_notifiers
from src.notifiers.email_notifier import EmailNotifier
from src.notifiers.generic_webhook_notifier import GenericWebhookNotifier
from src.notifiers.relay_webhook_notifier import RelayWebhookNotifier
from src.notifiers.telegram_notifier import TelegramNotifier
from src.notifiers.wecom_notifier import WeComNotifier
from src.sample_data import sample_alert
from src.secrets import load_env_file, read_env_values, write_env_values
from src.sources.library import test_feed_url
from src.ui.widgets import secret_line_edit, show_error, show_info
from src.utils.url_utils import is_valid_http_url

STATIC_TEXT_KEYS = {
    "General": "settings.tab.general",
    "LLM": "settings.tab.llm",
    "Alerts": "settings.tab.alerts",
    "Sources": "settings.tab.sources",
    "Notifications": "settings.tab.notifications",
    "Local Server / Advanced": "settings.tab.local_server",
    "Language, Translation, and Bias": "settings.language_translation_bias",
    "Global Output Language": "settings.global_output_language",
    "Enable Chinese/English Translation": "settings.enable_translation",
    "Translation Target Language": "settings.translation_target_language",
    "Enable Short Summary": "settings.enable_short_summary",
    "Enable Cross-source/Bias Context": "settings.enable_bias_context",
    "Bias Mode": "settings.bias_mode",
    "Minimum Sources per Cluster": "settings.minimum_sources_per_cluster",
    "LLM Settings": "llm_settings",
    "Mode": "settings.mode",
    "Primary Provider": "settings.primary_provider",
    "Fallback Providers": "settings.fallback_providers_llm",
    "OpenAI-compatible Base URL": "llm_base_url",
    "Model": "llm_model",
    "API Key": "llm_api_key",
    "Max Tokens": "settings.max_tokens",
    "Temperature": "settings.temperature",
    "Top P": "settings.top_p",
    "Presence Penalty": "settings.presence_penalty",
    "Timeout Seconds": "settings.timeout_seconds",
    "Max Retries": "settings.max_retries",
    "Retry Backoff Seconds": "settings.retry_backoff_seconds",
    "DeepSeek Fallback Provider": "settings.deepseek_provider",
    "Enable DeepSeek": "settings.enable_deepseek",
    "DeepSeek Model": "settings.deepseek_model",
    "DeepSeek API Key": "settings.deepseek_api_key",
    "DeepSeek Timeout Seconds": "settings.deepseek_timeout_seconds",
    "DeepSeek Max Retries": "settings.deepseek_max_retries",
    "DeepSeek Retry Backoff Seconds": "settings.deepseek_retry_backoff_seconds",
    "Help": "settings.help",
    "Alert Mode, Routing, and Quality Scoring": "settings.alert_quality",
    "Default Alert Mode": "settings.default_alert_mode",
    "Enable Notification Fallback": "settings.enable_notification_fallback",
    "Fallback Order": "settings.fallback_order",
    "Retry Attempts per Channel": "settings.retry_attempts_per_channel",
    "Retry Base Delay Seconds": "settings.retry_base_delay_seconds",
    "Official Source Boost": "settings.official_source_boost",
    "Company IR Boost": "settings.company_ir_boost",
    "Multi-source Confirmation Boost": "settings.multi_source_confirmation_boost",
    "Low-quality Source Penalty": "settings.low_quality_source_penalty",
    "Duplicate/Rewrite Penalty": "settings.duplicate_rewrite_penalty",
    "Event Cluster Strength Boost": "settings.event_cluster_strength_boost",
    "Whitelist Source Boost": "settings.whitelist_source_boost",
    "Exclude Blacklisted Sources": "settings.exclude_blacklisted_sources",
    "Whitelist Sources (one per line)": "settings.whitelist_sources",
    "Blacklist Sources (one per line)": "settings.blacklist_sources",
    "Category Priority (category: value)": "settings.category_priority",
    "Email Settings": "settings.email_settings",
    "Enable Email": "settings.enable_email",
    "SMTP Host": "settings.smtp_host",
    "SMTP Port": "settings.smtp_port",
    "Use TLS": "settings.use_tls",
    "Username": "settings.username",
    "App Password": "settings.app_password",
    "From Address": "settings.from_address",
    "To Addresses (one per line)": "settings.to_addresses",
    "Gmail App Password": "settings.gmail_app_password",
    "Outlook/SMTP Help": "settings.outlook_smtp_help",
    "WeCom Settings": "settings.wecom_settings",
    "Enable WeCom": "settings.enable_wecom",
    "Webhook URL": "webhook_url",
    "WeCom Bot Help": "settings.wecom_bot_help",
    "WeChat / QQ Relay Settings": "settings.relay_settings",
    "Enable WeChat Relay": "settings.enable_wechat_relay",
    "WeChat Provider": "settings.wechat_provider",
    "WeChat Webhook URL": "settings.wechat_webhook_url",
    "WeChat Help": "settings.wechat_help",
    "Enable QQ Relay": "settings.enable_qq_relay",
    "QQ Provider": "settings.qq_provider",
    "QQ Webhook URL": "settings.qq_webhook_url",
    "QQ Help": "settings.qq_help",
    "Telegram Settings": "settings.telegram_settings",
    "Enable Telegram": "settings.enable_telegram",
    "Bot Token": "telegram_token",
    "Chat ID": "telegram_chat_id",
    "BotFather Help": "settings.botfather_help",
    "Chat ID Help": "settings.chat_id_help",
    "Generic Webhook Settings": "settings.generic_webhook_settings",
    "Enable Generic Webhook": "settings.enable_generic_webhook",
    "Method": "settings.method",
    "Headers (key: value, one per line)": "settings.headers",
    "JSON Body Template": "settings.json_body_template",
    "News Sources": "settings.news_sources",
    "Global Public RSS (one per line)": "settings.global_public_rss",
    "Global Official RSS (one per line)": "settings.global_official_rss",
    "Enabled Packages (one per line)": "settings.enabled_packages",
    "Source Library": "settings.source_library",
    "Custom Sources": "settings.custom_sources",
    "X.com Social Source": "settings.x_social_source",
    "Enable X.com Recent Search": "settings.enable_x_recent_search",
    "X Bearer Token": "settings.x_bearer_token",
    "Max Posts per Topic per Run": "settings.x_max_posts_per_topic",
    "Include Retweets": "settings.x_include_retweets",
    "Minimum Author Followers": "settings.x_min_author_followers",
    "Trusted Accounts (one per line)": "settings.x_trusted_accounts",
    "Blocked Accounts (one per line)": "settings.x_blocked_accounts",
    "Recent Search Days Limit": "settings.x_recent_days_limit",
    "Enable X Cost Guard": "settings.x_enable_cost_guard",
    "Daily Max Read Posts": "settings.x_daily_max_read_posts",
    "Warn at Percent": "settings.x_warn_percent",
    "Source Name": "source_name",
    "RSS/Atom URL": "source_url",
    "Reliability 0-1": "settings.reliability",
    "Owner/Publisher": "settings.owner_publisher",
    "Bias Hint": "settings.bias_hint",
    "Default Language": "settings.default_language",
    "Enable/Disable Selected": "settings.enable_disable_selected",
    "Test Selected Source": "settings.test_selected_source",
    "Open Source Website": "settings.open_source_website",
    "RSS/Atom Help": "settings.rss_atom_help",
    "Add Source": "settings.add_source",
    "Remove Selected Source": "settings.remove_selected_source",
    "Runtime Settings": "settings.runtime_settings",
    "Default Poll Interval Seconds": "settings.default_poll_interval_seconds",
    "Default Relevance Threshold": "settings.default_relevance_threshold",
    "Max Alerts per Hour": "settings.max_alerts_per_hour",
    "Deduplication Window Hours": "settings.deduplication_window_hours",
    "Request Timeout Seconds": "settings.request_timeout_seconds",
    "Log Retention Days": "settings.log_retention_days",
    "Enable Local Live Server": "settings.enable_local_live_server",
    "Local Server Port": "settings.local_server_port",
    "Allow LAN Access": "settings.allow_lan_access",
    "Enable Browser Debug Details": "settings.enable_browser_debug_details",
    "Minimize to System Tray": "settings.minimize_to_system_tray",
    "Test LLM": "test_llm",
    "API Key Help": "settings.api_key_help",
    "Model Help": "model_help",
    "Test Email": "test_email",
    "Test WeCom": "test_wecom",
    "Test WeChat Relay": "test_wechat",
    "WeChat Relay Help": "settings.wechat_relay_help",
    "Test QQ Relay": "test_qq",
    "Qmsg Help": "settings.qmsg_help",
    "Test Telegram": "test_telegram",
    "Test Webhook": "test_webhook",
    "Save Settings": "save_settings",
    "GDELT Free News API": "settings.gdelt_free_news_api",
    "Google News RSS Keyword Source": "settings.google_news_rss_keyword_source",
    "Yahoo Finance RSS": "settings.yahoo_finance_rss",
    "Global Public AI/Tech RSS": "settings.global_public_ai_tech_rss",
    "Global Official RSS URLs": "settings.global_official_rss_urls",
    "Third-party relay services such as ServerChan, Chanify, and Qmsg receive notification content; check their privacy, availability, and rate limits.": "settings.relay_privacy_warning",
    "Use public RSS/Atom feeds, official public feeds, or documented free public APIs only. Do not add paywalled, login-only, private, or unauthorized scraped sources. Source packages enable curated groups without enabling every optional source.": "settings.source_rules_intro",
}

HELP_URLS = {
    "openai_keys": "https://platform.openai.com/api-keys",
    "openai_models": "https://platform.openai.com/docs/models",
    "deepseek_keys": "https://platform.deepseek.com/api_keys",
    "deepseek_models": "https://api-docs.deepseek.com/quick_start/pricing",
    "x_recent_search": "https://docs.x.com/x-api/posts/search/quickstart/recent-search",
    "gmail_app_password": "https://support.google.com/accounts/answer/185833",
    "outlook_smtp": "https://support.microsoft.com/office/pop-imap-and-smtp-settings-for-outlook-com-d088b986-291d-42b8-9564-9c414e2aa040",
    "telegram_botfather": "https://core.telegram.org/bots/tutorial",
    "telegram_chat_id": "https://api.telegram.org/",
    "wecom_bot": "https://developer.work.weixin.qq.com/document/path/91770",
    "serverchan": "https://sct.ftqq.com/",
    "chanify": "https://github.com/chanify/chanify",
    "qmsg": "https://qmsg.zendee.cn/",
    "rss": "https://rss.com/blog/how-do-rss-feeds-work/",
}


class SettingsBridge(QObject):
    test_result = Signal(str, str, bool)
    language_changed = Signal(str)


class SettingsPage(QWidget):
    def __init__(self, config_path: Path, runtime_dir: Path):
        super().__init__()
        self.config_path = config_path
        self.runtime_dir = runtime_dir
        self.env_path = runtime_dir / ".env"
        self.bridge = SettingsBridge()
        self.config = load_config(config_path)
        self.language = self.config.app.output_language
        self.env_values = read_env_values(self.env_path)
        self._loading_fields = False
        self._build_fields()
        self._build_layout()
        self._connect()
        self.load_into_fields()
        self.apply_language(self.language)

    def _build_fields(self) -> None:
        self.output_language = QComboBox()
        self.output_language.addItems(["Simplified Chinese", "English"])
        self.translation_enabled = QCheckBox("Enable Chinese/English Translation")
        self.translation_target = QComboBox()
        self.translation_target.addItems(["Simplified Chinese", "English"])
        self.summary_enabled = QCheckBox("Enable Short Summary")
        self.bias_enabled = QCheckBox("Enable Cross-source/Bias Context")
        self.bias_mode = QComboBox()
        self.bias_mode.addItems(["Single-source Hint", "Same-event Cluster"])
        self.bias_min_cluster = QSpinBox()
        self.bias_min_cluster.setRange(1, 10)
        self.alert_mode = QComboBox()
        self.alert_mode.addItems(["Fast Alert", "Full Analysis"])
        self.fallback_enabled = QCheckBox("Enable Notification Fallback")
        self.fallback_order = QLineEdit()
        self.retry_attempts = QSpinBox()
        self.retry_attempts.setRange(1, 10)
        self.retry_base_delay = QDoubleSpinBox()
        self.retry_base_delay.setRange(0, 60)
        self.retry_base_delay.setSingleStep(0.25)
        self.quality_official_boost = QDoubleSpinBox()
        self.quality_official_boost.setRange(0, 1)
        self.quality_official_boost.setSingleStep(0.01)
        self.quality_company_ir_boost = QDoubleSpinBox()
        self.quality_company_ir_boost.setRange(0, 1)
        self.quality_company_ir_boost.setSingleStep(0.01)
        self.quality_multi_boost = QDoubleSpinBox()
        self.quality_multi_boost.setRange(0, 1)
        self.quality_multi_boost.setSingleStep(0.01)
        self.quality_low_penalty = QDoubleSpinBox()
        self.quality_low_penalty.setRange(0, 1)
        self.quality_low_penalty.setSingleStep(0.01)
        self.quality_duplicate_penalty = QDoubleSpinBox()
        self.quality_duplicate_penalty.setRange(0, 1)
        self.quality_duplicate_penalty.setSingleStep(0.01)
        self.quality_cluster_strength_boost = QDoubleSpinBox()
        self.quality_cluster_strength_boost.setRange(0, 1)
        self.quality_cluster_strength_boost.setSingleStep(0.01)
        self.quality_whitelist_boost = QDoubleSpinBox()
        self.quality_whitelist_boost.setRange(0, 1)
        self.quality_whitelist_boost.setSingleStep(0.01)
        self.quality_blacklist_exclude = QCheckBox("Exclude Blacklisted Sources")
        self.quality_whitelist_sources = QTextEdit()
        self.quality_blacklist_sources = QTextEdit()
        self.quality_category_priority = QTextEdit()

        self.llm_provider = QComboBox()
        self.llm_provider.addItems(["openai", "deepseek", "openai_compatible"])
        self.llm_fallback_providers = QLineEdit()
        self.llm_preset = QComboBox()
        self.llm_preset.addItems(["Recommended", "Custom"])
        self.llm_base_url = QLineEdit()
        self.llm_model = QLineEdit()
        self.llm_api_key = secret_line_edit()
        self.llm_max_tokens = QSpinBox()
        self.llm_max_tokens.setRange(1, 200000)
        self.llm_temperature = QDoubleSpinBox()
        self.llm_temperature.setRange(0, 2)
        self.llm_temperature.setSingleStep(0.1)
        self.llm_top_p = QDoubleSpinBox()
        self.llm_top_p.setRange(0, 1)
        self.llm_top_p.setSingleStep(0.05)
        self.llm_presence_penalty = QDoubleSpinBox()
        self.llm_presence_penalty.setRange(-2, 2)
        self.llm_presence_penalty.setSingleStep(0.1)
        self.llm_timeout = QSpinBox()
        self.llm_timeout.setRange(1, 600)
        self.llm_max_retries = QSpinBox()
        self.llm_max_retries.setRange(0, 20)
        self.llm_retry_backoff = QDoubleSpinBox()
        self.llm_retry_backoff.setRange(0, 60)
        self.llm_retry_backoff.setSingleStep(0.25)
        self.deepseek_enabled = QCheckBox("Enable DeepSeek")
        self.deepseek_model = QLineEdit()
        self.deepseek_api_key = secret_line_edit()
        self.deepseek_timeout = QSpinBox()
        self.deepseek_timeout.setRange(1, 600)
        self.deepseek_max_retries = QSpinBox()
        self.deepseek_max_retries.setRange(0, 20)
        self.deepseek_retry_backoff = QDoubleSpinBox()
        self.deepseek_retry_backoff.setRange(0, 60)
        self.deepseek_retry_backoff.setSingleStep(0.25)
        self.test_llm_button = QPushButton("Test LLM")
        self.llm_keys_help_button = QPushButton("API Key Help")
        self.llm_models_help_button = QPushButton("Model Help")

        self.email_enabled = QCheckBox("Enable Email")
        self.email_preset = QComboBox()
        self.email_preset.addItems(["Recommended", "Custom"])
        self.email_host = QLineEdit()
        self.email_port = QSpinBox()
        self.email_port.setRange(1, 65535)
        self.email_tls = QCheckBox("Use TLS")
        self.email_username = QLineEdit()
        self.email_password = secret_line_edit()
        self.email_from = QLineEdit()
        self.email_to = QTextEdit()
        self.test_email_button = QPushButton("Test Email")
        self.email_gmail_help_button = QPushButton("Gmail App Password")
        self.email_outlook_help_button = QPushButton("Outlook/SMTP Help")

        self.wecom_enabled = QCheckBox("Enable WeCom")
        self.wecom_preset = QComboBox()
        self.wecom_preset.addItems(["Recommended", "Custom"])
        self.wecom_url = secret_line_edit()
        self.test_wecom_button = QPushButton("Test WeCom")
        self.wecom_help_button = QPushButton("WeCom Bot Help")

        self.wechat_enabled = QCheckBox("Enable WeChat Relay")
        self.wechat_provider = QComboBox()
        self.wechat_provider.addItems(["serverchan", "chanify"])
        self.wechat_url = secret_line_edit()
        self.test_wechat_button = QPushButton("Test WeChat Relay")
        self.wechat_help_button = QPushButton("WeChat Relay Help")

        self.qq_enabled = QCheckBox("Enable QQ Relay")
        self.qq_provider = QComboBox()
        self.qq_provider.addItems(["qmsg", "generic"])
        self.qq_url = secret_line_edit()
        self.test_qq_button = QPushButton("Test QQ Relay")
        self.qq_help_button = QPushButton("Qmsg Help")

        self.telegram_enabled = QCheckBox("Enable Telegram")
        self.telegram_preset = QComboBox()
        self.telegram_preset.addItems(["Recommended", "Custom"])
        self.telegram_token = secret_line_edit()
        self.telegram_chat_id = secret_line_edit()
        self.test_telegram_button = QPushButton("Test Telegram")
        self.telegram_bot_help_button = QPushButton("BotFather Help")
        self.telegram_chat_help_button = QPushButton("Chat ID Help")

        self.webhook_enabled = QCheckBox("Enable Generic Webhook")
        self.webhook_preset = QComboBox()
        self.webhook_preset.addItems(["Recommended", "Custom"])
        self.webhook_url = secret_line_edit()
        self.webhook_method = QComboBox()
        self.webhook_method.addItems(["POST", "PUT", "PATCH"])
        self.webhook_headers = QTextEdit()
        self.webhook_body_template = QTextEdit()
        self.test_webhook_button = QPushButton("Test Webhook")

        self.default_interval = QSpinBox()
        self.default_interval.setRange(15, 86400)
        self.min_relevance_score = QSpinBox()
        self.min_relevance_score.setRange(0, 100)
        self.max_alerts_per_hour = QSpinBox()
        self.max_alerts_per_hour.setRange(1, 1000)
        self.dedupe_hours = QSpinBox()
        self.dedupe_hours.setRange(1, 24 * 365)
        self.request_timeout = QSpinBox()
        self.request_timeout.setRange(1, 600)
        self.log_retention_days = QSpinBox()
        self.log_retention_days.setRange(1, 365)
        self.run_minimized_to_tray = QCheckBox("Minimize to System Tray")
        self.local_server_enabled = QCheckBox("Enable Local Live Server")
        self.local_server_port = QSpinBox()
        self.local_server_port.setRange(1024, 65535)
        self.local_server_lan = QCheckBox("Allow LAN Access")
        self.ui_debug_mode = QCheckBox("Enable Browser Debug Details")

        self.source_gdelt = QCheckBox("GDELT Free News API")
        self.source_google = QCheckBox("Google News RSS Keyword Source")
        self.source_yahoo = QCheckBox("Yahoo Finance RSS")
        self.source_public = QCheckBox("Global Public AI/Tech RSS")
        self.source_official = QCheckBox("Global Official RSS URLs")
        self.source_packages = QTextEdit()
        self.global_public_urls = QTextEdit()
        self.global_official_urls = QTextEdit()
        self.source_library = QListWidget()
        self.toggle_library_source_button = QPushButton("Enable/Disable Selected")
        self.test_library_source_button = QPushButton("Test Selected Source")
        self.open_source_website_button = QPushButton("Open Source Website")
        self.rss_help_button = QPushButton("RSS/Atom Help")
        self.x_enabled = QCheckBox("Enable X.com Recent Search")
        self.x_bearer_token = secret_line_edit()
        self.x_max_posts = QSpinBox()
        self.x_max_posts.setRange(1, 100)
        self.x_include_retweets = QCheckBox("Include Retweets")
        self.x_min_author_followers = QSpinBox()
        self.x_min_author_followers.setRange(0, 1_000_000_000)
        self.x_min_author_followers.setSpecialValueText("Any")
        self.x_trusted_accounts = QTextEdit()
        self.x_blocked_accounts = QTextEdit()
        self.x_recent_days = QSpinBox()
        self.x_recent_days.setRange(1, 7)
        self.x_cost_guard_enabled = QCheckBox("Enable X Cost Guard")
        self.x_daily_max_read_posts = QSpinBox()
        self.x_daily_max_read_posts.setRange(1, 1_000_000)
        self.x_warn_percent = QSpinBox()
        self.x_warn_percent.setRange(1, 100)
        self.custom_sources = QListWidget()
        self.custom_source_name = QLineEdit()
        self.custom_source_name.setPlaceholderText("Source name, for example Reuters RSS")
        self.custom_source_url = QLineEdit()
        self.custom_source_url.setPlaceholderText("https://example.com/feed.xml")
        self.custom_source_reliability = QDoubleSpinBox()
        self.custom_source_reliability.setRange(0, 1)
        self.custom_source_reliability.setSingleStep(0.05)
        self.custom_source_reliability.setValue(0.6)
        self.custom_source_owner = QLineEdit()
        self.custom_source_owner.setPlaceholderText("Owner or publisher, optional")
        self.custom_source_bias = QLineEdit()
        self.custom_source_bias.setPlaceholderText("Bias or framing hint, optional")
        self.custom_source_language = QComboBox()
        self.custom_source_language.addItems(["Auto", "Simplified Chinese", "English"])
        self.add_source_button = QPushButton("Add Source")
        self.remove_source_button = QPushButton("Remove Selected Source")

        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self._apply_field_metrics()

    def _build_layout(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        self.title_label = QLabel(text("settings", self.language))
        self.title_label.setObjectName("PageTitle")
        outer.addWidget(self.title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setUsesScrollButtons(True)
        self.settings_tabs.addTab(self._tab_with(self._language_group()), "General")
        self.settings_tabs.addTab(self._tab_with(self._llm_group()), "LLM")
        self.settings_tabs.addTab(self._tab_with(self._alerts_group()), "Alerts")
        self.settings_tabs.addTab(self._tab_with(self._sources_group(), self._social_sources_group()), "Sources")
        self.settings_tabs.addTab(
            self._tab_with(
                self._email_group(),
                self._telegram_group(),
                self._wecom_group(),
                self._relay_group(),
                self._webhook_group(),
            ),
            "Notifications",
        )
        self.settings_tabs.addTab(self._tab_with(self._runtime_group()), "Local Server / Advanced")
        layout.addWidget(self.settings_tabs)
        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.save_button)
        outer.addLayout(footer)

    def _apply_field_metrics(self) -> None:
        medium_editors = (
            self.quality_whitelist_sources,
            self.quality_blacklist_sources,
            self.quality_category_priority,
            self.email_to,
            self.webhook_headers,
            self.source_packages,
            self.global_public_urls,
            self.global_official_urls,
            self.x_trusted_accounts,
            self.x_blocked_accounts,
        )
        for editor in medium_editors:
            editor.setMinimumHeight(96)
            editor.setLineWrapMode(QTextEdit.WidgetWidth)
        self.webhook_body_template.setMinimumHeight(150)
        self.webhook_body_template.setLineWrapMode(QTextEdit.WidgetWidth)
        self.source_library.setMinimumHeight(240)
        self.custom_sources.setMinimumHeight(180)
        self.save_button.setMinimumWidth(180)
        self.save_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def apply_language(self, language: str) -> None:
        self.language = language
        self.title_label.setText(text("settings", language))
        self.save_button.setText(text("save", language))
        if hasattr(self, "settings_tabs"):
            keys = (
                "settings.tab.general",
                "settings.tab.llm",
                "settings.tab.alerts",
                "settings.tab.sources",
                "settings.tab.notifications",
                "settings.tab.local_server",
            )
            for index, key in enumerate(keys):
                self.settings_tabs.setTabText(index, text(key, language))
        self._translate_static_widgets(language)
        self._translate_placeholders(language)
        self._translate_language_combos(language)

    def _tab_with(self, *widgets: QWidget) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        return tab

    def _form_layout(self, parent: QWidget | None = None) -> QFormLayout:
        form = QFormLayout(parent)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        return form

    def _translate_static_widgets(self, language: str) -> None:
        mapping = _static_text_mapping(language)
        for group in self.findChildren(QGroupBox):
            group.setTitle(mapping.get(group.title(), group.title()))
        for label in self.findChildren(QLabel):
            label.setText(mapping.get(label.text(), label.text()))
        for checkbox in self.findChildren(QCheckBox):
            checkbox.setText(mapping.get(checkbox.text(), checkbox.text()))
        for button in self.findChildren(QPushButton):
            button.setText(mapping.get(button.text(), button.text()))

    def _translate_placeholders(self, language: str) -> None:
        self.llm_api_key.setPlaceholderText(text("settings.secret_placeholder", language))
        self.deepseek_api_key.setPlaceholderText(text("settings.secret_placeholder", language))
        self.email_password.setPlaceholderText(text("settings.secret_placeholder", language))
        self.wecom_url.setPlaceholderText(text("settings.secret_placeholder", language))
        self.wechat_url.setPlaceholderText(text("settings.secret_placeholder", language))
        self.qq_url.setPlaceholderText(text("settings.secret_placeholder", language))
        self.telegram_token.setPlaceholderText(text("settings.secret_placeholder", language))
        self.telegram_chat_id.setPlaceholderText(text("settings.secret_placeholder", language))
        self.webhook_url.setPlaceholderText(text("settings.secret_placeholder", language))
        self.x_bearer_token.setPlaceholderText(text("settings.secret_placeholder", language))
        self.custom_source_name.setPlaceholderText(text("settings.source_name_placeholder", language))
        self.custom_source_url.setPlaceholderText(text("settings.source_url_placeholder", language))
        self.custom_source_owner.setPlaceholderText(text("settings.owner_placeholder", language))
        self.custom_source_bias.setPlaceholderText(text("settings.bias_placeholder", language))

    def _language_group(self) -> QGroupBox:
        group = QGroupBox("Language, Translation, and Bias")
        form = self._form_layout(group)
        form.addRow("Global Output Language", self.output_language)
        form.addRow("", self.translation_enabled)
        form.addRow("Translation Target Language", self.translation_target)
        form.addRow("", self.summary_enabled)
        form.addRow("", self.bias_enabled)
        form.addRow("Bias Mode", self.bias_mode)
        form.addRow("Minimum Sources per Cluster", self.bias_min_cluster)
        return group

    def _llm_group(self) -> QGroupBox:
        group = QGroupBox("LLM Settings")
        form = self._form_layout(group)
        form.addRow("Mode", self.llm_preset)
        form.addRow("Primary Provider", self.llm_provider)
        form.addRow("Fallback Providers", self.llm_fallback_providers)
        form.addRow("OpenAI-compatible Base URL", self.llm_base_url)
        form.addRow("Model", self.llm_model)
        form.addRow("API Key", self.llm_api_key)
        form.addRow("Max Tokens", self.llm_max_tokens)
        form.addRow("Temperature", self.llm_temperature)
        form.addRow("Top P", self.llm_top_p)
        form.addRow("Presence Penalty", self.llm_presence_penalty)
        form.addRow("Timeout Seconds", self.llm_timeout)
        form.addRow("Max Retries", self.llm_max_retries)
        form.addRow("Retry Backoff Seconds", self.llm_retry_backoff)
        deepseek_group = QGroupBox("DeepSeek Fallback Provider")
        deepseek_form = self._form_layout(deepseek_group)
        deepseek_form.addRow("", self.deepseek_enabled)
        deepseek_form.addRow("DeepSeek Model", self.deepseek_model)
        deepseek_form.addRow("DeepSeek API Key", self.deepseek_api_key)
        deepseek_form.addRow("DeepSeek Timeout Seconds", self.deepseek_timeout)
        deepseek_form.addRow("DeepSeek Max Retries", self.deepseek_max_retries)
        deepseek_form.addRow("DeepSeek Retry Backoff Seconds", self.deepseek_retry_backoff)
        form.addRow(deepseek_group)
        form.addRow("", self.test_llm_button)
        helper_buttons = QHBoxLayout()
        helper_buttons.addWidget(self.llm_keys_help_button)
        helper_buttons.addWidget(self.llm_models_help_button)
        helper_buttons.addStretch(1)
        form.addRow("Help", helper_buttons)
        return group

    def _alerts_group(self) -> QGroupBox:
        group = QGroupBox("Alert Mode, Routing, and Quality Scoring")
        form = self._form_layout(group)
        form.addRow("Default Alert Mode", self.alert_mode)
        form.addRow("", self.fallback_enabled)
        form.addRow("Fallback Order", self.fallback_order)
        form.addRow("Retry Attempts per Channel", self.retry_attempts)
        form.addRow("Retry Base Delay Seconds", self.retry_base_delay)
        form.addRow("Official Source Boost", self.quality_official_boost)
        form.addRow("Company IR Boost", self.quality_company_ir_boost)
        form.addRow("Multi-source Confirmation Boost", self.quality_multi_boost)
        form.addRow("Low-quality Source Penalty", self.quality_low_penalty)
        form.addRow("Duplicate/Rewrite Penalty", self.quality_duplicate_penalty)
        form.addRow("Event Cluster Strength Boost", self.quality_cluster_strength_boost)
        form.addRow("Whitelist Source Boost", self.quality_whitelist_boost)
        form.addRow("", self.quality_blacklist_exclude)
        form.addRow("Whitelist Sources (one per line)", self.quality_whitelist_sources)
        form.addRow("Blacklist Sources (one per line)", self.quality_blacklist_sources)
        form.addRow("Category Priority (category: value)", self.quality_category_priority)
        return group

    def _email_group(self) -> QGroupBox:
        group = QGroupBox("Email Settings")
        form = self._form_layout(group)
        form.addRow("", self.email_enabled)
        form.addRow("Mode", self.email_preset)
        form.addRow("SMTP Host", self.email_host)
        form.addRow("SMTP Port", self.email_port)
        form.addRow("", self.email_tls)
        form.addRow("Username", self.email_username)
        form.addRow("App Password", self.email_password)
        form.addRow("From Address", self.email_from)
        form.addRow("To Addresses (one per line)", self.email_to)
        form.addRow("", self.test_email_button)
        helper_buttons = QHBoxLayout()
        helper_buttons.addWidget(self.email_gmail_help_button)
        helper_buttons.addWidget(self.email_outlook_help_button)
        helper_buttons.addStretch(1)
        form.addRow("Help", helper_buttons)
        return group

    def _wecom_group(self) -> QGroupBox:
        group = QGroupBox("WeCom Settings")
        form = self._form_layout(group)
        form.addRow("", self.wecom_enabled)
        form.addRow("Mode", self.wecom_preset)
        form.addRow("Webhook URL", self.wecom_url)
        form.addRow("", self.test_wecom_button)
        form.addRow("Help", self.wecom_help_button)
        return group

    def _relay_group(self) -> QGroupBox:
        group = QGroupBox("WeChat / QQ Relay Settings")
        form = self._form_layout(group)
        warning = QLabel(
            "Third-party relay services such as ServerChan, Chanify, and Qmsg receive notification content; check their privacy, availability, and rate limits."
        )
        warning.setWordWrap(True)
        form.addRow(warning)
        form.addRow("", self.wechat_enabled)
        form.addRow("WeChat Provider", self.wechat_provider)
        form.addRow("WeChat Webhook URL", self.wechat_url)
        form.addRow("", self.test_wechat_button)
        form.addRow("WeChat Help", self.wechat_help_button)
        form.addRow("", self.qq_enabled)
        form.addRow("QQ Provider", self.qq_provider)
        form.addRow("QQ Webhook URL", self.qq_url)
        form.addRow("", self.test_qq_button)
        form.addRow("QQ Help", self.qq_help_button)
        return group

    def _telegram_group(self) -> QGroupBox:
        group = QGroupBox("Telegram Settings")
        form = self._form_layout(group)
        form.addRow("", self.telegram_enabled)
        form.addRow("Mode", self.telegram_preset)
        form.addRow("Bot Token", self.telegram_token)
        form.addRow("Chat ID", self.telegram_chat_id)
        form.addRow("", self.test_telegram_button)
        helper_buttons = QHBoxLayout()
        helper_buttons.addWidget(self.telegram_bot_help_button)
        helper_buttons.addWidget(self.telegram_chat_help_button)
        helper_buttons.addStretch(1)
        form.addRow("Help", helper_buttons)
        return group

    def _webhook_group(self) -> QGroupBox:
        group = QGroupBox("Generic Webhook Settings")
        form = self._form_layout(group)
        form.addRow("", self.webhook_enabled)
        form.addRow("Mode", self.webhook_preset)
        form.addRow("Webhook URL", self.webhook_url)
        form.addRow("Method", self.webhook_method)
        form.addRow("Headers (key: value, one per line)", self.webhook_headers)
        form.addRow("JSON Body Template", self.webhook_body_template)
        form.addRow("", self.test_webhook_button)
        return group

    def _sources_group(self) -> QGroupBox:
        group = QGroupBox("News Sources")
        layout = QVBoxLayout(group)
        intro = QLabel(
            "Public RSS/Atom feeds and free public news APIs are supported. Do not add unauthorized, paywalled, or login-only scraped sources."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        for checkbox in (
            self.source_gdelt,
            self.source_google,
            self.source_yahoo,
            self.source_public,
            self.source_official,
        ):
            layout.addWidget(checkbox)
        form = self._form_layout()
        form.addRow("Global Public RSS (one per line)", self.global_public_urls)
        form.addRow("Global Official RSS (one per line)", self.global_official_urls)
        form.addRow("Enabled Packages (one per line)", self.source_packages)
        form.addRow("Source Library", self.source_library)
        form.addRow("Custom Sources", self.custom_sources)
        form.addRow("Source Name", self.custom_source_name)
        form.addRow("RSS/Atom URL", self.custom_source_url)
        form.addRow("Reliability 0-1", self.custom_source_reliability)
        form.addRow("Owner/Publisher", self.custom_source_owner)
        form.addRow("Bias Hint", self.custom_source_bias)
        form.addRow("Default Language", self.custom_source_language)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_source_button)
        buttons.addWidget(self.remove_source_button)
        buttons.addWidget(self.toggle_library_source_button)
        buttons.addWidget(self.test_library_source_button)
        buttons.addWidget(self.open_source_website_button)
        buttons.addWidget(self.rss_help_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return group

    def _social_sources_group(self) -> QGroupBox:
        group = QGroupBox("X.com Social Source")
        form = self._form_layout(group)
        form.addRow("", self.x_enabled)
        form.addRow("X Bearer Token", self.x_bearer_token)
        form.addRow("Max Posts per Topic per Run", self.x_max_posts)
        form.addRow("", self.x_include_retweets)
        form.addRow("Minimum Author Followers", self.x_min_author_followers)
        form.addRow("Trusted Accounts (one per line)", self.x_trusted_accounts)
        form.addRow("Blocked Accounts (one per line)", self.x_blocked_accounts)
        form.addRow("Recent Search Days Limit", self.x_recent_days)
        form.addRow("", self.x_cost_guard_enabled)
        form.addRow("Daily Max Read Posts", self.x_daily_max_read_posts)
        form.addRow("Warn at Percent", self.x_warn_percent)
        return group

    def _runtime_group(self) -> QGroupBox:
        group = QGroupBox("Runtime Settings")
        form = self._form_layout(group)
        form.addRow("Default Poll Interval Seconds", self.default_interval)
        form.addRow("Default Relevance Threshold", self.min_relevance_score)
        form.addRow("Max Alerts per Hour", self.max_alerts_per_hour)
        form.addRow("Deduplication Window Hours", self.dedupe_hours)
        form.addRow("Request Timeout Seconds", self.request_timeout)
        form.addRow("Log Retention Days", self.log_retention_days)
        form.addRow("", self.local_server_enabled)
        form.addRow("Local Server Port", self.local_server_port)
        form.addRow("", self.local_server_lan)
        form.addRow("", self.ui_debug_mode)
        form.addRow("", self.run_minimized_to_tray)
        return group

    def _connect(self) -> None:
        self.save_button.clicked.connect(lambda: self.save_settings(False))
        self.test_llm_button.clicked.connect(self.test_llm)
        self.test_email_button.clicked.connect(lambda: self.test_single("email"))
        self.test_wecom_button.clicked.connect(lambda: self.test_single("wecom"))
        self.test_wechat_button.clicked.connect(lambda: self.test_single("wechat"))
        self.test_qq_button.clicked.connect(lambda: self.test_single("qq"))
        self.test_telegram_button.clicked.connect(lambda: self.test_single("telegram"))
        self.test_webhook_button.clicked.connect(lambda: self.test_single("generic_webhook"))
        self.bridge.test_result.connect(self._show_test_result)
        self.output_language.currentTextChanged.connect(self._language_selection_changed)
        self.llm_preset.currentIndexChanged.connect(self._apply_preset_states)
        self.email_preset.currentIndexChanged.connect(self._apply_preset_states)
        self.wecom_preset.currentIndexChanged.connect(self._apply_preset_states)
        self.telegram_preset.currentIndexChanged.connect(self._apply_preset_states)
        self.webhook_preset.currentIndexChanged.connect(self._apply_preset_states)
        self.add_source_button.clicked.connect(self._add_custom_source)
        self.remove_source_button.clicked.connect(self._remove_custom_source)
        self.toggle_library_source_button.clicked.connect(self._toggle_library_source)
        self.test_library_source_button.clicked.connect(self._test_selected_library_source)
        self.open_source_website_button.clicked.connect(self._open_selected_library_source)
        self.llm_keys_help_button.clicked.connect(lambda: self._open_help("openai_keys"))
        self.llm_models_help_button.clicked.connect(lambda: self._open_help("openai_models"))
        self.email_gmail_help_button.clicked.connect(lambda: self._open_help("gmail_app_password"))
        self.email_outlook_help_button.clicked.connect(lambda: self._open_help("outlook_smtp"))
        self.telegram_bot_help_button.clicked.connect(lambda: self._open_help("telegram_botfather"))
        self.telegram_chat_help_button.clicked.connect(lambda: self._open_help("telegram_chat_id"))
        self.wecom_help_button.clicked.connect(lambda: self._open_help("wecom_bot"))
        self.wechat_help_button.clicked.connect(lambda: self._open_help("serverchan"))
        self.qq_help_button.clicked.connect(lambda: self._open_help("qmsg"))
        self.rss_help_button.clicked.connect(lambda: self._open_help("rss"))

    def load_into_fields(self) -> None:
        self._loading_fields = True
        config = self.config
        try:
            self.output_language.setCurrentText(_language_label(config.app.output_language))
            self.translation_enabled.setChecked(config.enrichment.translation_enabled)
            self.translation_target.setCurrentText(_language_label(config.enrichment.target_language))
            self.summary_enabled.setChecked(config.enrichment.summary_enabled)
            self.bias_enabled.setChecked(config.bias.enabled)
            self.bias_mode.setCurrentText(
                "Same-event Cluster" if config.bias.mode == "cluster" else "Single-source Hint"
            )
            self.bias_min_cluster.setValue(config.bias.min_cluster_size)
            self.alert_mode.setCurrentText(
                "Full Analysis" if config.alerts.default_mode == "full_analysis" else "Fast Alert"
            )
            self.fallback_enabled.setChecked(config.notifications.fallback_enabled)
            self.fallback_order.setText(", ".join(config.notifications.fallback_order))
            self.retry_attempts.setValue(config.notifications.retry_attempts)
            self.retry_base_delay.setValue(config.notifications.retry_base_delay_seconds)
            self.quality_official_boost.setValue(config.quality.official_source_boost)
            self.quality_company_ir_boost.setValue(config.quality.company_ir_boost)
            self.quality_multi_boost.setValue(config.quality.multi_source_confirmation_boost)
            self.quality_low_penalty.setValue(config.quality.low_quality_source_penalty)
            self.quality_duplicate_penalty.setValue(config.quality.duplicate_rewrite_penalty)
            self.quality_cluster_strength_boost.setValue(config.quality.event_cluster_strength_boost)
            self.quality_whitelist_boost.setValue(config.quality.whitelist_boost)
            self.quality_blacklist_exclude.setChecked(config.quality.blacklist_exclude)
            self.quality_whitelist_sources.setPlainText("\n".join(config.quality.whitelist_sources))
            self.quality_blacklist_sources.setPlainText("\n".join(config.quality.blacklist_sources))
            self.quality_category_priority.setPlainText(
                "\n".join(f"{key}: {value}" for key, value in config.quality.category_priority.items())
            )

            self.llm_preset.setCurrentText(_preset_label(config.llm.preset))
            self.llm_provider.setCurrentText(config.llm.provider)
            self.llm_fallback_providers.setText(", ".join(config.llm.fallback_providers))
            self.llm_base_url.setText(config.llm.base_url)
            self.llm_model.setText(config.llm.model)
            self.llm_api_key.setText(self.env_values.get(config.llm.api_key_env, ""))
            self.llm_max_tokens.setValue(config.llm.max_tokens)
            self.llm_temperature.setValue(config.llm.temperature)
            self.llm_top_p.setValue(config.llm.top_p)
            self.llm_presence_penalty.setValue(config.llm.presence_penalty)
            self.llm_timeout.setValue(config.llm.timeout_seconds)
            self.llm_max_retries.setValue(config.llm.max_retries)
            self.llm_retry_backoff.setValue(config.llm.retry_backoff_seconds)
            deepseek = _llm_provider_settings(config.llm.providers, "deepseek")
            self.deepseek_enabled.setChecked(deepseek.enabled)
            self.deepseek_model.setText(deepseek.model)
            self.deepseek_api_key.setText(self.env_values.get(deepseek.api_key_env, ""))
            self.deepseek_timeout.setValue(deepseek.timeout_seconds)
            self.deepseek_max_retries.setValue(deepseek.max_retries)
            self.deepseek_retry_backoff.setValue(deepseek.retry_backoff_seconds)

            email = config.notifiers.email
            self.email_enabled.setChecked(email.enabled)
            self.email_preset.setCurrentText(_preset_label(email.preset))
            self.email_host.setText(email.smtp_host)
            self.email_port.setValue(email.smtp_port)
            self.email_tls.setChecked(email.use_tls)
            self.email_username.setText(self.env_values.get(email.username_env, ""))
            self.email_password.setText(self.env_values.get(email.password_env, ""))
            self.email_from.setText(self.env_values.get(email.from_addr_env, ""))
            self.email_to.setPlainText("\n".join(email.to_addrs))

            self.wecom_enabled.setChecked(config.notifiers.wecom.enabled)
            self.wecom_preset.setCurrentText(_preset_label(config.notifiers.wecom.preset))
            self.wecom_url.setText(self.env_values.get(config.notifiers.wecom.webhook_url_env, ""))

            self.wechat_enabled.setChecked(config.notifiers.wechat.enabled)
            self.wechat_provider.setCurrentText(config.notifiers.wechat.provider)
            self.wechat_url.setText(self.env_values.get(config.notifiers.wechat.webhook_url_env, ""))

            self.qq_enabled.setChecked(config.notifiers.qq.enabled)
            self.qq_provider.setCurrentText(
                config.notifiers.qq.provider if config.notifiers.qq.provider != "qmsg" else "qmsg"
            )
            self.qq_url.setText(self.env_values.get(config.notifiers.qq.webhook_url_env, ""))

            self.telegram_enabled.setChecked(config.notifiers.telegram.enabled)
            self.telegram_preset.setCurrentText(_preset_label(config.notifiers.telegram.preset))
            self.telegram_token.setText(self.env_values.get(config.notifiers.telegram.bot_token_env, ""))
            self.telegram_chat_id.setText(self.env_values.get(config.notifiers.telegram.chat_id_env, ""))

            generic = config.notifiers.generic_webhook
            self.webhook_enabled.setChecked(generic.enabled)
            self.webhook_preset.setCurrentText(_preset_label(generic.preset))
            self.webhook_url.setText(self.env_values.get(generic.url_env, ""))
            self.webhook_method.setCurrentText(generic.method)
            self.webhook_headers.setPlainText(
                "\n".join(f"{key}: {value}" for key, value in generic.headers.items())
            )
            self.webhook_body_template.setPlainText(generic.body_template)

            self.default_interval.setValue(config.monitor.default_interval_seconds)
            self.min_relevance_score.setValue(config.monitor.min_relevance_score)
            self.max_alerts_per_hour.setValue(config.monitor.max_alerts_per_hour)
            self.dedupe_hours.setValue(config.monitor.deduplicate_hours)
            self.request_timeout.setValue(config.monitor.request_timeout_seconds)
            self.log_retention_days.setValue(config.monitor.log_retention_days)
            self.run_minimized_to_tray.setChecked(config.app.run_minimized_to_tray)
            self.local_server_enabled.setChecked(config.local_server.enabled)
            self.local_server_port.setValue(config.local_server.port)
            self.local_server_lan.setChecked(config.local_server.allow_lan)
            self.ui_debug_mode.setChecked(config.ui.debug_mode)
            self.source_gdelt.setChecked(config.sources.gdelt.enabled)
            self.source_google.setChecked(config.sources.google_news_rss.enabled)
            self.source_yahoo.setChecked(config.sources.yahoo_finance_rss.enabled)
            self.source_public.setChecked(config.sources.public_rss.enabled)
            self.source_official.setChecked(config.sources.official_rss.enabled)
            self.source_packages.setPlainText("\n".join(config.sources.enabled_packages))
            self.global_public_urls.setPlainText("\n".join(config.sources.public_rss.urls))
            self.global_official_urls.setPlainText("\n".join(config.sources.official_rss.urls))
            x = config.social_sources.x
            self.x_enabled.setChecked(x.enabled)
            self.x_bearer_token.setText(self.env_values.get(x.bearer_token_env, ""))
            self.x_max_posts.setValue(x.max_posts_per_topic_per_run)
            self.x_include_retweets.setChecked(x.include_retweets)
            self.x_min_author_followers.setValue(x.min_author_followers or 0)
            self.x_trusted_accounts.setPlainText("\n".join(x.trusted_accounts))
            self.x_blocked_accounts.setPlainText("\n".join(x.blocked_accounts))
            self.x_recent_days.setValue(x.search_recent_days_limit)
            self.x_cost_guard_enabled.setChecked(x.cost_guard.enabled)
            self.x_daily_max_read_posts.setValue(x.cost_guard.daily_max_read_posts)
            self.x_warn_percent.setValue(x.cost_guard.warn_when_reaching_percent)
            self._render_source_library(config.sources.library)
            self._render_custom_sources(config.sources.custom_sources)
            self._apply_preset_states()
        finally:
            self._loading_fields = False

    def save_settings(self, silent: bool = False) -> bool:
        try:
            config = load_config(self.config_path)
            config.app.output_language = _language_value(self.output_language.currentText())
            config.enrichment.translation_enabled = self.translation_enabled.isChecked()
            config.enrichment.target_language = _language_value(self.translation_target.currentText())
            config.enrichment.summary_enabled = self.summary_enabled.isChecked()
            config.bias.enabled = self.bias_enabled.isChecked()
            config.bias.mode = "cluster" if self.bias_mode.currentText() == "Same-event Cluster" else "single"
            config.bias.min_cluster_size = self.bias_min_cluster.value()
            config.alerts.default_mode = "full_analysis" if self.alert_mode.currentText() == "Full Analysis" else "fast"
            config.notifications.fallback_enabled = self.fallback_enabled.isChecked()
            config.notifications.fallback_order = _comma_or_lines(self.fallback_order.text())
            config.notifications.retry_attempts = self.retry_attempts.value()
            config.notifications.retry_base_delay_seconds = self.retry_base_delay.value()
            config.quality.official_source_boost = self.quality_official_boost.value()
            config.quality.company_ir_boost = self.quality_company_ir_boost.value()
            config.quality.multi_source_confirmation_boost = self.quality_multi_boost.value()
            config.quality.low_quality_source_penalty = self.quality_low_penalty.value()
            config.quality.duplicate_rewrite_penalty = self.quality_duplicate_penalty.value()
            config.quality.event_cluster_strength_boost = self.quality_cluster_strength_boost.value()
            config.quality.whitelist_boost = self.quality_whitelist_boost.value()
            config.quality.blacklist_exclude = self.quality_blacklist_exclude.isChecked()
            config.quality.whitelist_sources = _lines(self.quality_whitelist_sources.toPlainText())
            config.quality.blacklist_sources = _lines(self.quality_blacklist_sources.toPlainText())
            config.quality.category_priority = _mapping(self.quality_category_priority.toPlainText())
            for topic in config.topics:
                topic.output_language = config.app.output_language

            config.llm.preset = _preset_value(self.llm_preset.currentText())
            config.llm.provider = self.llm_provider.currentText().strip() or "openai_compatible"
            config.llm.fallback_providers = _comma_or_lines(self.llm_fallback_providers.text())
            config.llm.base_url = self.llm_base_url.text().strip()
            config.llm.model = self.llm_model.text().strip()
            config.llm.max_tokens = self.llm_max_tokens.value()
            config.llm.temperature = self.llm_temperature.value()
            config.llm.top_p = self.llm_top_p.value()
            config.llm.presence_penalty = self.llm_presence_penalty.value()
            config.llm.timeout_seconds = self.llm_timeout.value()
            config.llm.max_retries = self.llm_max_retries.value()
            config.llm.retry_backoff_seconds = self.llm_retry_backoff.value()
            config.llm.providers["openai"] = LLMProviderSettings(
                enabled=True,
                api_key_env="OPENAI_API_KEY",
                base_url=self.llm_base_url.text().strip() or "https://api.openai.com/v1",
                model=self.llm_model.text().strip() or "gpt-4.1-mini",
                timeout_seconds=self.llm_timeout.value(),
                max_retries=self.llm_max_retries.value(),
                retry_backoff_seconds=self.llm_retry_backoff.value(),
                structured_outputs=config.llm.structured_outputs,
            )
            deepseek_selected = config.llm.provider == "deepseek" or "deepseek" in config.llm.fallback_providers
            config.llm.providers["deepseek"] = LLMProviderSettings(
                enabled=self.deepseek_enabled.isChecked() or deepseek_selected,
                api_key_env="DEEPSEEK_API_KEY",
                base_url="https://api.deepseek.com",
                model=self.deepseek_model.text().strip() or "deepseek-v4-flash",
                timeout_seconds=self.deepseek_timeout.value(),
                max_retries=self.deepseek_max_retries.value(),
                retry_backoff_seconds=self.deepseek_retry_backoff.value(),
                structured_outputs=True,
            )
            _sync_primary_llm_settings(config)

            email = config.notifiers.email
            email.preset = _preset_value(self.email_preset.currentText())
            email.enabled = self.email_enabled.isChecked()
            email.smtp_host = self.email_host.text().strip()
            email.smtp_port = self.email_port.value()
            email.use_tls = self.email_tls.isChecked()
            email.to_addrs = _lines(self.email_to.toPlainText())

            config.notifiers.wecom.preset = _preset_value(self.wecom_preset.currentText())
            config.notifiers.wecom.enabled = self.wecom_enabled.isChecked()
            config.notifiers.wechat.enabled = self.wechat_enabled.isChecked()
            config.notifiers.wechat.provider = self.wechat_provider.currentText()
            config.notifiers.qq.enabled = self.qq_enabled.isChecked()
            config.notifiers.qq.provider = "qmsg" if self.qq_provider.currentText() == "qmsg" else "generic"
            config.notifiers.telegram.preset = _preset_value(self.telegram_preset.currentText())
            config.notifiers.telegram.enabled = self.telegram_enabled.isChecked()
            config.notifiers.generic_webhook.preset = _preset_value(self.webhook_preset.currentText())
            config.notifiers.generic_webhook.enabled = self.webhook_enabled.isChecked()
            config.notifiers.generic_webhook.method = self.webhook_method.currentText()
            config.notifiers.generic_webhook.headers = _headers(self.webhook_headers.toPlainText())
            config.notifiers.generic_webhook.body_template = (
                self.webhook_body_template.toPlainText().strip() or "default"
            )

            config.monitor.default_interval_seconds = self.default_interval.value()
            config.monitor.min_relevance_score = self.min_relevance_score.value()
            config.monitor.max_alerts_per_hour = self.max_alerts_per_hour.value()
            config.monitor.deduplicate_hours = self.dedupe_hours.value()
            config.monitor.request_timeout_seconds = self.request_timeout.value()
            config.monitor.log_retention_days = self.log_retention_days.value()
            config.app.run_minimized_to_tray = self.run_minimized_to_tray.isChecked()
            config.local_server.enabled = self.local_server_enabled.isChecked()
            config.local_server.port = self.local_server_port.value()
            config.local_server.allow_lan = self.local_server_lan.isChecked()
            config.local_server.host = "0.0.0.0" if config.local_server.allow_lan else "127.0.0.1"
            config.ui.debug_mode = self.ui_debug_mode.isChecked()
            config.sources.gdelt.enabled = self.source_gdelt.isChecked()
            config.sources.google_news_rss.enabled = self.source_google.isChecked()
            config.sources.yahoo_finance_rss.enabled = self.source_yahoo.isChecked()
            config.sources.public_rss.enabled = self.source_public.isChecked()
            config.sources.public_rss.urls = _lines(self.global_public_urls.toPlainText())
            config.sources.official_rss.enabled = self.source_official.isChecked()
            config.sources.official_rss.urls = _lines(self.global_official_urls.toPlainText())
            config.sources.enabled_packages = _lines(self.source_packages.toPlainText())
            config.sources.library = self._source_library_from_list()
            config.sources.custom_sources = self._custom_sources_from_list()
            config.social_sources.x.enabled = self.x_enabled.isChecked()
            config.social_sources.x.bearer_token_env = "X_BEARER_TOKEN"
            config.social_sources.x.max_posts_per_topic_per_run = self.x_max_posts.value()
            config.social_sources.x.include_retweets = self.x_include_retweets.isChecked()
            config.social_sources.x.min_author_followers = self.x_min_author_followers.value() or None
            config.social_sources.x.trusted_accounts = _lines(self.x_trusted_accounts.toPlainText())
            config.social_sources.x.blocked_accounts = _lines(self.x_blocked_accounts.toPlainText())
            config.social_sources.x.search_recent_days_limit = self.x_recent_days.value()
            config.social_sources.x.cost_guard.enabled = self.x_cost_guard_enabled.isChecked()
            config.social_sources.x.cost_guard.daily_max_read_posts = self.x_daily_max_read_posts.value()
            config.social_sources.x.cost_guard.warn_when_reaching_percent = self.x_warn_percent.value()

            self._validate_enabled_channel_fields(config)
            validate_config(config)
            save_config(config, self.config_path)
            self.config = config
            self._write_env_from_fields(config)
            load_env_file(self.env_path)
            self.language = config.app.output_language
            self.apply_language(self.language)
            self.bridge.language_changed.emit(self.language)
            if not silent:
                show_info(self, text("saved_title", self.language), text("settings.saved_message", self.language))
            return True
        except (ConfigError, ValueError) as exc:
            show_error(self, text("settings.invalid_settings_title", self.language), str(exc))
            return False

    def test_llm(self) -> None:
        if not self.save_settings(True):
            return

        def task() -> tuple[bool, str]:
            LLMClient(self.config.llm).test()
            return True, text("settings.llm_test_succeeded", self.language)

        self._run_test_async(text("settings.llm_test_title", self.language), task)

    def test_single(self, name: str) -> None:
        if not self.save_settings(True):
            return

        def task() -> tuple[bool, str]:
            alert = sample_alert()
            notifier = {
                "email": EmailNotifier(self.config.notifiers.email),
                "wecom": WeComNotifier(self.config.notifiers.wecom, self.config.monitor.request_timeout_seconds),
                "wechat": RelayWebhookNotifier(
                    self.config.notifiers.wechat, self.config.monitor.request_timeout_seconds
                ),
                "qq": RelayWebhookNotifier(self.config.notifiers.qq, self.config.monitor.request_timeout_seconds),
                "telegram": TelegramNotifier(
                    self.config.notifiers.telegram, self.config.monitor.request_timeout_seconds
                ),
                "generic_webhook": GenericWebhookNotifier(
                    self.config.notifiers.generic_webhook, self.config.monitor.request_timeout_seconds
                ),
            }[name]
            result = notifier.send_test() if hasattr(notifier, "send_test") else notifier.send(alert)
            if result.success:
                return True, text("settings.notification_test_succeeded", self.language, name=result.notifier_name)
            return False, result.error_message or text("settings.unknown_error", self.language)

        self._run_test_async(text("settings.notification_test_title", self.language), task)

    def run_enabled_notification_tests(self) -> None:
        if not self.save_settings(True):
            return

        def task() -> tuple[bool, str]:
            results: list[str] = []
            has_failure = False
            for notifier in build_notifiers(self.config.notifiers, self.config.monitor.request_timeout_seconds):
                result = notifier.send_test() if hasattr(notifier, "send_test") else notifier.send(sample_alert())
                if result.success:
                    status = text("settings.success", self.language)
                else:
                    has_failure = True
                    status = text("settings.failed", self.language, error=result.error_message)
                results.append(f"{result.notifier_name}: {status}")
            if not results:
                return True, text("settings.no_notification_channels", self.language)
            return not has_failure, "\n".join(results)

        self._run_test_async(text("settings.notification_test_results_title", self.language), task)

    def _run_test_async(self, title: str, task) -> None:
        self._set_test_buttons_enabled(False)

        def target() -> None:
            try:
                success, message = task()
            except Exception as exc:  # noqa: BLE001 - result is shown to the user
                success, message = False, str(exc)
            self.bridge.test_result.emit(title, message, success)

        threading.Thread(target=target, name="settings-test-worker", daemon=True).start()

    def _show_test_result(self, title: str, message: str, success: bool) -> None:
        self._set_test_buttons_enabled(True)
        if success:
            show_info(self, title, message)
        else:
            show_error(self, title, message)

    def _set_test_buttons_enabled(self, enabled: bool) -> None:
        for button in (
            self.test_llm_button,
            self.test_email_button,
            self.test_wecom_button,
            self.test_wechat_button,
            self.test_qq_button,
            self.test_telegram_button,
            self.test_webhook_button,
        ):
            button.setEnabled(enabled)

    def _apply_preset_states(self) -> None:
        llm_recommended = _preset_value(self.llm_preset.currentText()) == "recommended"
        for widget in (
            self.llm_provider,
            self.llm_fallback_providers,
            self.llm_base_url,
            self.llm_max_tokens,
            self.llm_temperature,
            self.llm_top_p,
            self.llm_presence_penalty,
            self.llm_timeout,
            self.llm_max_retries,
            self.llm_retry_backoff,
        ):
            widget.setEnabled(not llm_recommended)
        if llm_recommended:
            self.llm_provider.setCurrentText("openai_compatible")
            self.llm_fallback_providers.clear()
            self.llm_base_url.setText("https://api.openai.com/v1")
            self.llm_max_tokens.setValue(1024)
            self.llm_temperature.setValue(0.7)
            self.llm_top_p.setValue(1.0)
            self.llm_presence_penalty.setValue(0.0)
            self.llm_timeout.setValue(30)
            self.llm_max_retries.setValue(3)
            self.llm_retry_backoff.setValue(2.0)

        email_recommended = _preset_value(self.email_preset.currentText()) == "recommended"
        for widget in (self.email_host, self.email_port, self.email_tls):
            widget.setEnabled(not email_recommended)
        if email_recommended:
            self.email_host.setText("smtp.gmail.com")
            self.email_port.setValue(587)
            self.email_tls.setChecked(True)

        webhook_recommended = _preset_value(self.webhook_preset.currentText()) == "recommended"
        for widget in (self.webhook_method, self.webhook_headers, self.webhook_body_template):
            widget.setEnabled(not webhook_recommended)
        if webhook_recommended:
            self.webhook_method.setCurrentText("POST")
            self.webhook_headers.clear()
            self.webhook_body_template.setPlainText("default")

    def _language_selection_changed(self, label: str) -> None:
        if self._loading_fields:
            return
        language = _language_value(label)
        if language == self.config.app.output_language:
            self.apply_language(language)
            return
        if self._save_language_only(language):
            self._set_language_combo_value(self.translation_target, language, self.language)
            self.apply_language(language)
            self.bridge.language_changed.emit(language)

    def _save_language_only(self, language: str) -> bool:
        try:
            config = load_config(self.config_path)
            config.app.output_language = language
            config.enrichment.target_language = language
            for topic in config.topics:
                topic.output_language = language
            validate_config(config)
            save_config(config, self.config_path)
            self.config = config
            self.language = language
            return True
        except (ConfigError, ValueError) as exc:
            show_error(self, text("settings.invalid_settings_title", self.language), str(exc))
            return False

    def _translate_language_combos(self, language: str) -> None:
        self._set_language_combo_value(
            self.output_language,
            _language_value(self.output_language.currentText()),
            language,
        )
        self._set_language_combo_value(
            self.translation_target,
            _language_value(self.translation_target.currentText()),
            language,
        )
        custom_language = self.custom_source_language.currentText()
        custom_value = None if _is_auto_language_label(custom_language) else _language_value(custom_language)
        self._set_language_combo_value(self.custom_source_language, custom_value, language, include_auto=True)

    def _set_language_combo_value(
        self,
        combo: QComboBox,
        value: str | None,
        language: str,
        *,
        include_auto: bool = False,
    ) -> None:
        previous = combo.blockSignals(True)
        try:
            combo.clear()
            if include_auto:
                combo.addItem(text("auto", language))
            combo.addItems([_language_label("zh-CN", language), _language_label("en", language)])
            target = text("auto", language) if value is None else _language_label(value, language)
            combo.setCurrentText(target)
        finally:
            combo.blockSignals(previous)

    def _render_source_library(self, sources: list[SourceLibraryItem]) -> None:
        self.source_library.clear()
        for source in sources:
            self._add_library_item(source)

    def _add_library_item(self, source: SourceLibraryItem) -> None:
        from PySide6.QtWidgets import QListWidgetItem

        item = QListWidgetItem(_library_item_text(source))
        item.setData(Qt.ItemDataRole.UserRole, source)
        self.source_library.addItem(item)

    def _source_library_from_list(self) -> list[SourceLibraryItem]:
        sources: list[SourceLibraryItem] = []
        for index in range(self.source_library.count()):
            source = self.source_library.item(index).data(Qt.ItemDataRole.UserRole)
            if isinstance(source, SourceLibraryItem):
                sources.append(source)
        return sources

    def _selected_library_item(self) -> tuple[int, SourceLibraryItem] | None:
        row = self.source_library.currentRow()
        if row < 0:
            return None
        source = self.source_library.item(row).data(Qt.ItemDataRole.UserRole)
        if not isinstance(source, SourceLibraryItem):
            return None
        return row, source

    def _toggle_library_source(self) -> None:
        selected = self._selected_library_item()
        if not selected:
            return
        row, source = selected
        updated = replace(source, enabled=not source.enabled)
        item = self.source_library.item(row)
        item.setText(_library_item_text(updated))
        item.setData(Qt.ItemDataRole.UserRole, updated)

    def _test_selected_library_source(self) -> None:
        selected = self._selected_library_item()
        if not selected:
            show_error(
                self,
                text("settings.no_source_selected_title", self.language),
                text("settings.no_source_selected_message", self.language),
            )
            return
        _, source = selected
        if source.kind != "rss":
            show_info(
                self,
                text("settings.website_only_source_title", self.language),
                text("settings.website_only_source_message", self.language),
            )
            return

        def task() -> tuple[bool, str]:
            result = test_feed_url(source.url, self.request_timeout.value())
            sample = "\n".join(result.get("sample_titles", [])[:3])
            return bool(result.get("ok")), f"{source.name}: {result.get('entries', 0)} entries\n{sample}"

        self._run_test_async(text("settings.source_test_title", self.language), task)

    def _open_selected_library_source(self) -> None:
        selected = self._selected_library_item()
        if not selected:
            show_error(
                self,
                text("settings.no_source_selected_title", self.language),
                text("settings.no_source_selected_message", self.language),
            )
            return
        _, source = selected
        QDesktopServices.openUrl(QUrl(source.website_url or source.url))

    def _open_help(self, key: str) -> None:
        url = HELP_URLS.get(key)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _validate_enabled_channel_fields(self, config) -> None:
        if config.notifiers.email.enabled:
            if not self.email_username.text().strip() or not self.email_password.text().strip():
                raise ValueError(text("settings.email_credentials_required", self.language))
            if not config.notifiers.email.to_addrs:
                raise ValueError(text("settings.email_recipients_required", self.language))
        if config.notifiers.wecom.enabled and not self.wecom_url.text().strip():
            raise ValueError(text("settings.wecom_webhook_required", self.language))
        if config.notifiers.wechat.enabled and not self.wechat_url.text().strip():
            raise ValueError(text("settings.wechat_webhook_required", self.language))
        if config.notifiers.qq.enabled and not self.qq_url.text().strip():
            raise ValueError(text("settings.qq_webhook_required", self.language))
        if config.notifiers.telegram.enabled and (
            not self.telegram_token.text().strip() or not self.telegram_chat_id.text().strip()
        ):
            raise ValueError(text("settings.telegram_credentials_required", self.language))
        if config.notifiers.generic_webhook.enabled and not self.webhook_url.text().strip():
            raise ValueError(text("settings.generic_webhook_required", self.language))
        if config.social_sources.x.enabled and not self.x_bearer_token.text().strip():
            raise ValueError(text("settings.x_bearer_token_required", self.language))

    def _render_custom_sources(self, sources: list[CustomNewsSourceConfig]) -> None:
        self.custom_sources.clear()
        for source in sources:
            enabled = "Enabled" if source.enabled else "Disabled"
            language = (
                _language_label(source.default_language, self.language)
                if source.default_language
                else text("auto", self.language)
            )
            self.custom_sources.addItem(
                f"{enabled} | {source.name} | {source.url} | {source.reliability_score:.2f} | "
                f"{source.ownership or ''} | {source.bias_hint or ''} | {language}"
            )

    def _custom_sources_from_list(self) -> list[CustomNewsSourceConfig]:
        sources: list[CustomNewsSourceConfig] = []
        for index in range(self.custom_sources.count()):
            parts = [part.strip() for part in self.custom_sources.item(index).text().split("|")]
            if len(parts) >= 3:
                reliability = float(parts[3]) if len(parts) > 3 and parts[3] else 0.6
                ownership = parts[4] if len(parts) > 4 and parts[4] else None
                bias_hint = parts[5] if len(parts) > 5 and parts[5] else None
                language = (
                    _language_value(parts[6])
                    if len(parts) > 6 and not _is_auto_language_label(parts[6])
                    else None
                )
                sources.append(
                    CustomNewsSourceConfig(
                        name=parts[1],
                        url=parts[2],
                        enabled=parts[0] == "Enabled",
                        reliability_score=reliability,
                        ownership=ownership,
                        bias_hint=bias_hint,
                        default_language=language,
                    )
                )
        return sources

    def _add_custom_source(self) -> None:
        name = self.custom_source_name.text().strip()
        url = self.custom_source_url.text().strip()
        if not name or not url:
            show_error(
                self,
                text("settings.invalid_source_title", self.language),
                text("settings.invalid_source_message", self.language),
            )
            return
        if not is_valid_http_url(url):
            show_error(
                self,
                text("settings.invalid_url_title", self.language),
                text("settings.invalid_url_message", self.language),
            )
            return
        if any(
            source.name.casefold() == name.casefold() or source.url.casefold() == url.casefold()
            for source in self._custom_sources_from_list()
        ):
            show_error(
                self,
                text("settings.duplicate_source_title", self.language),
                text("settings.duplicate_source_message", self.language),
            )
            return
        reliability = self.custom_source_reliability.value()
        owner = self.custom_source_owner.text().strip()
        bias = self.custom_source_bias.text().strip()
        language = self.custom_source_language.currentText()
        self.custom_sources.addItem(f"Enabled | {name} | {url} | {reliability:.2f} | {owner} | {bias} | {language}")
        self.custom_source_name.clear()
        self.custom_source_url.clear()
        self.custom_source_owner.clear()
        self.custom_source_bias.clear()

    def _remove_custom_source(self) -> None:
        row = self.custom_sources.currentRow()
        if row >= 0:
            self.custom_sources.takeItem(row)

    def _write_env_from_fields(self, config) -> None:
        values = read_env_values(self.env_path)
        updates = {
            config.llm.api_key_env: self.llm_api_key.text(),
            "DEEPSEEK_API_KEY": self.deepseek_api_key.text(),
            "X_BEARER_TOKEN": self.x_bearer_token.text(),
            config.notifiers.email.username_env: self.email_username.text(),
            config.notifiers.email.password_env: self.email_password.text(),
            config.notifiers.email.from_addr_env: self.email_from.text(),
            config.notifiers.wecom.webhook_url_env: self.wecom_url.text(),
            config.notifiers.wechat.webhook_url_env: self.wechat_url.text(),
            config.notifiers.qq.webhook_url_env: self.qq_url.text(),
            config.notifiers.telegram.bot_token_env: self.telegram_token.text(),
            config.notifiers.telegram.chat_id_env: self.telegram_chat_id.text(),
            config.notifiers.generic_webhook.url_env: self.webhook_url.text(),
        }
        values.update({key: value for key, value in updates.items() if key})
        write_env_values(self.env_path, values)
        os.environ.update(values)


def _preset_label(value: str) -> str:
    return "Custom" if value == "custom" else "Recommended"


def _preset_value(label: str) -> str:
    return "custom" if label == "Custom" else "recommended"


def _llm_provider_settings(providers: dict[str, LLMProviderSettings], name: str) -> LLMProviderSettings:
    provider = providers.get(name)
    if provider:
        return provider
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


def _sync_primary_llm_settings(config) -> None:
    provider = config.llm.providers.get(config.llm.provider)
    if not provider:
        return
    config.llm.api_key_env = provider.api_key_env
    config.llm.base_url = provider.base_url
    config.llm.model = provider.model
    config.llm.timeout_seconds = provider.timeout_seconds
    config.llm.max_retries = provider.max_retries
    config.llm.retry_backoff_seconds = provider.retry_backoff_seconds
    config.llm.structured_outputs = provider.structured_outputs


def _language_label(value: str | None, language: str | None = None) -> str:
    return text("language_en", language or "en") if value == "en" else text("language_zh_cn", language or "en")


def _language_value(label: str) -> str:
    value = label.strip()
    normalized = value.replace("_", "-").casefold()
    english_labels = {"en", "english", text("language_en", "en").casefold(), text("language_en", "zh-CN").casefold()}
    chinese_labels = {
        "zh-cn",
        "zh",
        "simplified chinese",
        text("language_zh_cn", "en").casefold(),
        text("language_zh_cn", "zh-CN").casefold(),
    }
    if normalized in english_labels:
        return "en"
    if normalized in chinese_labels:
        return "zh-CN"
    return "zh-CN"


def _is_auto_language_label(label: str) -> bool:
    normalized = label.strip().casefold()
    return normalized in {"auto", text("auto", "en").casefold(), text("auto", "zh-CN").casefold()}


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _comma_or_lines(text: str) -> list[str]:
    return [part.strip() for chunk in text.splitlines() for part in chunk.split(",") if part.strip()]


def _mapping(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for line in _lines(text):
        if ":" not in line:
            raise ValueError(f"Invalid mapping format: {line}")
        key, value = line.split(":", 1)
        values[key.strip()] = float(value.strip())
    return values


def _headers(text: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in _lines(text):
        if ":" not in line:
            raise ValueError(f"Invalid header format: {line}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def _static_text_mapping(language: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for literal, key in STATIC_TEXT_KEYS.items():
        target = text(key, language)
        mapping[literal] = target
        mapping[text(key, "en")] = target
        mapping[text(key, "zh-CN")] = target
    return mapping


def _library_item_text(source: SourceLibraryItem) -> str:
    enabled = "Enabled" if source.enabled else "Disabled"
    return (
        f"{enabled} | {source.id} | {source.name} | {source.category} | {source.language} | "
        f"{source.source_type} | Tier {source.source_tier} | {source.source_role} | "
        f"{source.propaganda_risk} | {source.reliability_score:.2f} | {source.ownership or ''} | "
        f"{source.bias_hint or ''} | {source.url}"
    )
