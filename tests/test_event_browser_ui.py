from __future__ import annotations

from src.i18n import catalog
from src.realtime import _index_html


def test_browser_ui_has_event_cluster_cards_without_raw_json_primary_label():
    html = _index_html()

    assert 'id="eventRows"' in html
    assert 'data-i18n="event_clusters"' in html
    assert "renderEventCards" in html
    assert "Raw event JSON" not in html
    assert "JSON.stringify(event)" not in html


def test_event_locale_keys_exist_in_english_and_chinese():
    required = {
        "event_clusters",
        "grouped_articles",
        "latest_update_time",
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
