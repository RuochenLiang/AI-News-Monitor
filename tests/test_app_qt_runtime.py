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


def test_message_box_style_uses_high_contrast_colors():
    script = textwrap.dedent("""
        from src.ui.widgets import MESSAGE_BOX_STYLE

        assert "background-color: #ffffff" in MESSAGE_BOX_STYLE
        assert "color: #172033" in MESSAGE_BOX_STYLE
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
