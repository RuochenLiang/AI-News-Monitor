from __future__ import annotations

from src.config import save_config
from src.i18n import catalog
from src.models import AppConfig, AppSettings, RuntimeStatus
from src.realtime import _index_html, _status_payload


def test_browser_ui_has_event_cluster_cards_without_raw_json_primary_label():
    html = _index_html()

    assert 'id="eventRows"' in html
    assert 'data-i18n="event_clusters"' in html
    assert "renderEventCards" in html
    assert 'id="sourceSelectionRows"' in html
    assert "renderSourceSelection" in html
    assert "Raw event JSON" not in html
    assert "JSON.stringify(event)" not in html


def test_browser_ui_uses_calm_cool_background_and_larger_feedback_regions():
    html = _index_html()

    assert "--bg:#eef5f2" in html
    assert "feedback-grid" in html
    assert 'class="list tall" id="events"' in html
    assert 'class="card list tall" id="logRows"' in html
    assert "max-width:min(680px,calc(100vw - 36px))" in html


def test_browser_ui_uses_safe_responsive_grid_constraints():
    html = _index_html()

    assert "minmax(min(100%,280px),1fr)" in html
    assert "minmax(min(100%,320px),1fr)" in html
    assert "min-height:clamp(220px,42vh,360px)" in html
    assert "@media (max-width:520px)" in html
    assert ".actions button,.actions a{width:100%}" in html


def test_source_package_rows_use_dedicated_typography():
    html = _index_html()

    assert ".package-row{display:grid" in html
    assert ".package-title{display:block;font:inherit;font-weight:650" in html
    assert ".package-detail{font-size:13px;line-height:1.5" in html
    assert ".package-warning{color:var(--amber)}" in html
    assert ".row,.diagnostic-row,.package-row{grid-template-columns:1fr}" in html
    assert 'class="package-row"' in html
    assert 'class="package-title safe-long-text"' in html
    assert 'class="package-detail safe-long-text"' in html
    assert "statusBadge(pkg.enabled ? 'enabled' : 'disabled', lang)" in html
    assert 'class="small-button package-action"' in html


def test_browser_language_refresh_uses_live_config_and_retranslated_events(tmp_path):
    html = _index_html()
    config = AppConfig(app=AppSettings(output_language="en"))
    config.alerts.default_mode = "full_analysis"
    config.ui.debug_mode = True
    config.sources.enabled_packages = ["global-news-starter"]
    config_path = tmp_path / "config.yaml"
    save_config(config, config_path)

    payload = _status_payload(RuntimeStatus(output_language="zh-CN", alert_mode="fast"), config_path)

    assert payload["output_language"] == "en"
    assert payload["alert_mode"] == "full_analysis"
    assert payload["ui_debug_mode"] is True
    assert payload["source_packages_enabled"] == ["global-news-starter"]
    assert "const STATUS_REFRESH_MS = 1500" in html
    assert "const SETUP_REFRESH_MS = 5000" in html
    assert "setInterval(refresh, STATUS_REFRESH_MS)" in html
    assert "setInterval(loadSetup, SETUP_REFRESH_MS)" in html
    assert "if(previousLang !== currentLang){ loadSetup(); }" in html
    assert "summary:eventSummary" not in html
    assert "eventItems.unshift({name, at:new Date().toISOString(), details:payload})" in html
    assert "eventSummary(item.name, item.details || {})" in html


def test_event_locale_keys_exist_in_english_and_chinese():
    required = {
        "auto",
        "event_clusters",
        "grouped_articles",
        "latest_update_time",
        "confidence_score",
        "relevance_score",
        "verification_status",
        "source_comparison",
        "source_selection",
        "selection_reason",
        "expected_value",
        "auto_selected_source",
        "manual_source",
        "priority",
        "risk",
        "empty_source_selection",
        "verified",
        "developing",
        "unconfirmed",
        "low_confidence",
        "timeline",
        "sources",
        "relation_reason",
        "empty_event_clusters",
        "alert.current_status",
        "alert.timeline",
        "alert.sources",
        "alert.relation_reason",
        "alert.suggested_follow_up",
    }

    for language in ("en", "zh-CN"):
        labels = catalog(language)
        missing = sorted(key for key in required if not labels.get(key))
        assert not missing
