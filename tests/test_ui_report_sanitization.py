from __future__ import annotations

from src.config import parse_config, save_config
from src.models import AppConfig, RuntimeStatus, UiSettings
from src.realtime import _index_html, _status_payload, status_to_dict


def test_ui_debug_mode_defaults_to_false():
    config = parse_config({})

    assert config.ui.debug_mode is False


def test_browser_report_ui_keeps_raw_json_out_of_primary_event_cards():
    html = _index_html()

    assert "Raw event JSON" not in html
    assert "JSON.stringify(event)" not in html
    assert "show_details" in html


def test_browser_diagnostics_are_hidden_unless_debug_mode_is_enabled():
    html = _index_html()

    assert "let debugMode = false;" in html
    assert "if(!debugMode) return '';" in html
    assert "debugMode = s.ui_debug_mode === true;" in html
    assert "debugMode = setup.ui?.debug_mode === true;" in html


def test_status_serializes_ui_debug_mode_flag():
    assert status_to_dict(RuntimeStatus())["ui_debug_mode"] is False
    assert status_to_dict(RuntimeStatus(ui_debug_mode=True))["ui_debug_mode"] is True


def test_status_payload_uses_current_config_debug_mode(tmp_path):
    config_path = tmp_path / "config.yaml"
    save_config(AppConfig(ui=UiSettings(debug_mode=True)), config_path)

    payload = _status_payload(RuntimeStatus(ui_debug_mode=False), config_path)

    assert payload["ui_debug_mode"] is True
