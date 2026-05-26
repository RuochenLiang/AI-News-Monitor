from __future__ import annotations

import os
import socket
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from src import app as app_module

ROOT = Path(__file__).resolve().parents[1]


def test_prepend_env_path_adds_path_once(monkeypatch, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    monkeypatch.setenv("QT_PLUGIN_PATH", str(second))

    app_module._prepend_env_path("QT_PLUGIN_PATH", first)
    app_module._prepend_env_path("QT_PLUGIN_PATH", first)

    assert os.environ["QT_PLUGIN_PATH"].split(os.pathsep) == [str(first), str(second)]


def test_configure_qt_runtime_noop_off_macos(monkeypatch):
    monkeypatch.setattr(app_module.sys, "platform", "linux")
    monkeypatch.delenv("QT_QPA_PLATFORM_PLUGIN_PATH", raising=False)

    app_module._configure_qt_runtime()

    assert "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ


def test_settings_page_static_text_uses_locale_resources(monkeypatch, tmp_path):
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from src import app as app_module

        app_module._configure_qt_runtime()

        from PySide6.QtWidgets import QApplication, QGroupBox

        from src.config import save_config
        from src.i18n import text
        from src.models import AppConfig, AppSettings
        from src.ui.settings_page import SettingsPage

        runtime_dir = Path({str(tmp_path)!r})
        app = QApplication.instance() or QApplication([])
        config_path = runtime_dir / "config.yaml"
        save_config(AppConfig(app=AppSettings(output_language="zh-CN")), config_path)
        (runtime_dir / ".env").write_text("", encoding="utf-8")

        page = SettingsPage(config_path, runtime_dir)
        page.apply_language("zh-CN")
        group_titles = [group.title() for group in page.findChildren(QGroupBox)]

        assert app is not None
        assert text("settings.language_translation_bias", "zh-CN") in group_titles
        assert page.test_llm_button.text() == text("test_llm", "zh-CN")
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_settings_page_static_text_keys_exist():
    script = textwrap.dedent("""
        from src.i18n import catalog
        from src.ui.settings_page import STATIC_TEXT_KEYS

        english = catalog("en")
        chinese = catalog("zh-CN")

        for key in STATIC_TEXT_KEYS.values():
            assert key in english
            assert key in chinese
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_desktop_sources_keep_window_adaptation_hooks():
    dashboard = (ROOT / "src" / "ui" / "dashboard_page.py").read_text(encoding="utf-8")
    topics = (ROOT / "src" / "ui" / "topics_page.py").read_text(encoding="utf-8")
    settings = (ROOT / "src" / "ui" / "settings_page.py").read_text(encoding="utf-8")
    logs = (ROOT / "src" / "ui" / "logs_page.py").read_text(encoding="utf-8")

    assert "def _dashboard_columns" in dashboard
    assert "def _action_columns" in dashboard
    assert "self.body_splitter.setOrientation(orientation)" in dashboard
    assert "Qt.Vertical if narrow else Qt.Horizontal" in dashboard
    assert "form.setRowWrapPolicy(QFormLayout.WrapLongRows)" in topics
    assert "self.splitter.setOrientation(orientation)" in topics
    assert "form.setRowWrapPolicy(QFormLayout.WrapLongRows)" in settings
    assert "self.settings_tabs.setUsesScrollButtons(True)" in settings
    assert "self.text.setMinimumHeight(220)" in logs


def test_desktop_sources_keep_language_refresh_hooks():
    settings = (ROOT / "src" / "ui" / "settings_page.py").read_text(encoding="utf-8")
    main_window = (ROOT / "src" / "ui" / "main_window.py").read_text(encoding="utf-8")
    scheduler = (ROOT / "src" / "scheduler.py").read_text(encoding="utf-8")
    realtime = (ROOT / "src" / "realtime.py").read_text(encoding="utf-8")

    assert "self.output_language.currentTextChanged.connect(self._language_selection_changed)" in settings
    assert "def _save_language_only" in settings
    assert "config.enrichment.target_language = language" in settings
    assert "topic.output_language = language" in settings
    assert "def _translate_language_combos" in settings
    assert "self.tray_actions" in main_window
    assert "self.worker.reload_runtime_settings()" in main_window
    assert "def reload_runtime_settings" in scheduler
    assert '"output_language": self.status.output_language' in scheduler
    assert 'payload["output_language"] = config.app.output_language' in realtime


def test_settings_page_saves_deepseek_and_x_configuration(tmp_path):
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from PySide6.QtWidgets import QApplication

        from src.config import load_config, save_config
        from src.models import AppConfig, EmailSettings, NotifierSettings
        from src.secrets import read_env_values
        from src.ui.settings_page import SettingsPage

        runtime_dir = Path({str(tmp_path)!r})
        app = QApplication.instance() or QApplication([])
        config_path = runtime_dir / "config.yaml"
        save_config(AppConfig(notifiers=NotifierSettings(email=EmailSettings(enabled=False))), config_path)
        (runtime_dir / ".env").write_text("", encoding="utf-8")

        page = SettingsPage(config_path, runtime_dir)
        page.llm_preset.setCurrentText("Custom")
        page.llm_provider.setCurrentText("deepseek")
        page.llm_fallback_providers.setText("openai")
        page.llm_base_url.setText("https://api.openai.com/v1")
        page.llm_model.setText("gpt-4.1-mini")
        page.llm_api_key.setText("sk-openai")
        page.llm_max_retries.setValue(4)
        page.llm_retry_backoff.setValue(1.25)
        page.deepseek_enabled.setChecked(True)
        page.deepseek_model.setText("deepseek-v4-pro")
        page.deepseek_api_key.setText("sk-deepseek")
        page.deepseek_timeout.setValue(90)
        page.deepseek_max_retries.setValue(5)
        page.deepseek_retry_backoff.setValue(3.5)
        page.x_enabled.setChecked(True)
        page.x_bearer_token.setText("x-token")
        page.x_max_posts.setValue(12)
        page.x_include_retweets.setChecked(True)
        page.x_min_author_followers.setValue(1000)
        page.x_trusted_accounts.setPlainText("XDevelopers\\nOpenAI")
        page.x_blocked_accounts.setPlainText("spam")
        page.x_recent_days.setValue(3)
        page.x_cost_guard_enabled.setChecked(True)
        page.x_daily_max_read_posts.setValue(250)
        page.x_warn_percent.setValue(75)
        page.ui_debug_mode.setChecked(True)

        assert app is not None
        assert page.save_settings(True) is True

        saved = load_config(config_path)
        env = read_env_values(runtime_dir / ".env")
        assert saved.llm.provider == "deepseek"
        assert saved.llm.fallback_providers == ["openai"]
        assert saved.llm.model == "deepseek-v4-pro"
        assert saved.llm.base_url == "https://api.deepseek.com"
        assert saved.llm.providers["deepseek"].enabled is True
        assert saved.llm.providers["deepseek"].timeout_seconds == 90
        assert saved.llm.providers["deepseek"].max_retries == 5
        assert saved.llm.providers["deepseek"].retry_backoff_seconds == 3.5
        assert saved.social_sources.x.enabled is True
        assert saved.social_sources.x.max_posts_per_topic_per_run == 12
        assert saved.social_sources.x.include_retweets is True
        assert saved.social_sources.x.min_author_followers == 1000
        assert saved.social_sources.x.trusted_accounts == ["XDevelopers", "OpenAI"]
        assert saved.social_sources.x.blocked_accounts == ["spam"]
        assert saved.social_sources.x.search_recent_days_limit == 3
        assert saved.social_sources.x.cost_guard.daily_max_read_posts == 250
        assert saved.social_sources.x.cost_guard.warn_when_reaching_percent == 75
        assert saved.ui.debug_mode is True
        assert env["DEEPSEEK_API_KEY"] == "sk-deepseek"
        assert env["X_BEARER_TOKEN"] == "x-token"
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_topics_page_exposes_next_version_topic_schema(tmp_path):
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from PySide6.QtWidgets import QApplication

        from src.config import save_config
        from src.models import AppConfig, TopicConfig
        from src.ui.topics_page import TopicsPage

        runtime_dir = Path({str(tmp_path)!r})
        app = QApplication.instance() or QApplication([])
        config_path = runtime_dir / "config.yaml"
        save_config(
            AppConfig(
                topics=[
                    TopicConfig(
                        name="Policy",
                        enabled=True,
                        prompt="Track policy.",
                        keywords=["policy"],
                        id="policy",
                        source_mode="hybrid",
                        domains=["politics", "public_policy"],
                        preferred_regions=["US", "EU"],
                        social_enabled=True,
                        min_confidence_score=0.7,
                        report_include_timeline=True,
                        report_include_source_comparison=True,
                        report_include_user_action=False,
                    )
                ]
            ),
            config_path,
        )

        page = TopicsPage(config_path)
        topic = page._topic_from_form()

        assert app is not None
        assert page.topic_tabs.count() == 3
        assert page.source_mode.currentText() == "hybrid"
        assert topic.id == "policy"
        assert topic.domains == ["politics", "public_policy"]
        assert topic.preferred_regions == ["US", "EU"]
        assert topic.social_enabled is True
        assert topic.min_confidence_score == 0.7
        assert topic.report_include_user_action is False
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_dashboard_and_topic_pages_adapt_to_narrow_windows(tmp_path):
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        from src.config import save_config
        from src.models import AppConfig, TopicConfig
        from src.ui.dashboard_page import DashboardPage
        from src.ui.topics_page import TopicsPage

        runtime_dir = Path({str(tmp_path)!r})
        app = QApplication.instance() or QApplication([])
        config_path = runtime_dir / "config.yaml"
        save_config(
            AppConfig(topics=[TopicConfig(name="Policy", enabled=True, prompt="Track policy.", keywords=["policy"])]),
            config_path,
        )

        dashboard = DashboardPage()
        dashboard.resize(360, 500)
        dashboard.show()
        app.processEvents()
        dashboard._apply_adaptive_layout()

        topics = TopicsPage(config_path)
        topics.resize(540, 520)
        topics.show()
        app.processEvents()
        topics._apply_adaptive_layout()

        assert app is not None
        assert dashboard._stat_columns <= 2
        assert dashboard.body_splitter.orientation() == Qt.Vertical
        assert topics.splitter.orientation() == Qt.Vertical

        dashboard.resize(980, 640)
        topics.resize(980, 640)
        app.processEvents()
        dashboard._apply_adaptive_layout()
        topics._apply_adaptive_layout()

        assert dashboard._stat_columns >= 3
        assert dashboard.body_splitter.orientation() == Qt.Horizontal
        assert topics.splitter.orientation() == Qt.Horizontal
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_settings_forms_wrap_long_rows_for_small_windows(tmp_path):
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from PySide6.QtWidgets import QApplication, QFormLayout

        from src.config import save_config
        from src.models import AppConfig
        from src.ui.settings_page import SettingsPage

        runtime_dir = Path({str(tmp_path)!r})
        app = QApplication.instance() or QApplication([])
        config_path = runtime_dir / "config.yaml"
        save_config(AppConfig(), config_path)
        (runtime_dir / ".env").write_text("", encoding="utf-8")

        page = SettingsPage(config_path, runtime_dir)
        forms = page.findChildren(QFormLayout)

        assert app is not None
        assert forms
        assert all(form.rowWrapPolicy() == QFormLayout.WrapLongRows for form in forms)
        assert page.settings_tabs.usesScrollButtons() is True
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_message_box_style_uses_high_contrast_colors():
    script = textwrap.dedent("""
        from src.ui.widgets import MESSAGE_BOX_STYLE

        assert "background-color: #ffffff" in MESSAGE_BOX_STYLE
        assert "color: #172033" in MESSAGE_BOX_STYLE
        assert "min-width: 560px" in MESSAGE_BOX_STYLE
        assert "min-height: 240px" in MESSAGE_BOX_STYLE
        assert "QMessageBox QLabel" in MESSAGE_BOX_STYLE
        """)
    result = _run_qt_script(script)
    assert result.returncode == 0, result.stderr + result.stdout


def test_main_reports_qt_runtime_configuration_error(monkeypatch, tmp_path, capsys):
    def raise_qt_error() -> None:
        raise RuntimeError("Qt platform plugin is unavailable.")

    monkeypatch.setattr(app_module, "assert_runtime_dependencies", lambda: None)
    monkeypatch.setattr(app_module, "ensure_runtime_files", lambda: tmp_path)
    monkeypatch.setattr(app_module, "setup_logging", lambda runtime_dir: None)
    monkeypatch.setattr(app_module, "_configure_qt_runtime", raise_qt_error)

    assert app_module.main() == 1
    assert "Qt platform plugin is unavailable." in capsys.readouterr().err


def test_main_window_startup_and_close_exit_cleanly(tmp_path):
    port = _free_local_port()
    script = textwrap.dedent(f"""
        import os
        import sys
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        from src import app as app_module

        app_module._configure_qt_runtime()

        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from src.config import save_config
        from src.models import AppConfig, AppSettings, LocalServerSettings
        from src.ui.main_window import MainWindow

        runtime_dir = Path({str(tmp_path)!r})
        save_config(
            AppConfig(
                app=AppSettings(run_minimized_to_tray=False),
                local_server=LocalServerSettings(port={port}),
            ),
            runtime_dir / "config.yaml",
        )
        (runtime_dir / ".env").write_text("", encoding="utf-8")

        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        window = MainWindow(runtime_dir)

        def timeout() -> None:
            print("timeout waiting for clean close", file=sys.stderr)
            app.exit(124)

        QTimer.singleShot(100, window.close)
        QTimer.singleShot(5000, timeout)
        exit_code = app.exec()
        if window.worker._event_server is not None:
            print("event server still running after close", file=sys.stderr)
            raise SystemExit(125)
        print(f"closed cleanly with code {{exit_code}}")
        raise SystemExit(exit_code)
        """)
    result = _run_qt_script(script, timeout=10)
    assert result.returncode == 0, result.stderr + result.stdout


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS Qt platform plugin check")
def test_configure_qt_runtime_sets_macos_plugin_paths(monkeypatch):
    monkeypatch.delenv("QT_PLUGIN_PATH", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM_PLUGIN_PATH", raising=False)
    monkeypatch.delenv("QT_MAC_WANTS_LAYER", raising=False)

    app_module._configure_qt_runtime()

    platforms_dir = Path(os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"])
    assert (platforms_dir / "libqcocoa.dylib").exists()
    assert str(platforms_dir.parent) in os.environ["QT_PLUGIN_PATH"].split(os.pathsep)
    assert os.environ["QT_MAC_WANTS_LAYER"] == "1"


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError:
            pytest.skip("Local sandbox does not allow binding a loopback port.")
        return int(sock.getsockname()[1])


def _run_qt_script(script: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    if sys.platform == "darwin" and not os.environ.get("CI") and os.environ.get("AI_NEWS_MONITOR_RUN_QT_SMOKE") != "1":
        pytest.skip("Local macOS Qt smoke tests are opt-in to avoid native PySide crash dialogs.")

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env={**os.environ, "QT_MAC_WANTS_LAYER": "1", "QT_QPA_PLATFORM": "offscreen"},
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        if sys.platform == "darwin" and os.environ.get("CI"):
            pytest.skip("Qt event loop did not exit in the macOS headless CI runner.")
        raise
    output = result.stderr + result.stdout
    if result.returncode != 0 and "Incompatible processor" in output:
        pytest.skip("Qt wheel is not compatible with this processor in the current runner.")
    return result
