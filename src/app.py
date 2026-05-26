from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from src.config import ensure_runtime_files
from src.dependency_check import assert_runtime_dependencies
from src.logging_setup import setup_logging


def _prepend_env_path(name: str, path: Path) -> None:
    value = str(path)
    existing = [item for item in os.environ.get(name, "").split(os.pathsep) if item]
    if value not in existing:
        os.environ[name] = os.pathsep.join([value, *existing])


def _configure_qt_runtime() -> None:
    """Make PySide6's macOS platform plugin discoverable before QApplication."""
    if sys.platform != "darwin":
        return

    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

    try:
        import PySide6
    except ImportError as exc:
        raise RuntimeError(
            "PySide6 is not installed. Recreate the virtual environment and run "
            "`python -m pip install -r requirements.txt`."
        ) from exc

    package_file = getattr(PySide6, "__file__", None)
    if package_file:
        package_dir = Path(package_file).resolve().parent
    else:
        package_paths = list(getattr(PySide6, "__path__", []))
        if not package_paths:
            raise RuntimeError("PySide6 package location could not be determined.")
        package_dir = Path(package_paths[0]).resolve()

    plugins_dir = _usable_qt_plugins_dir(package_dir / "Qt" / "plugins", getattr(PySide6, "__version__", "unknown"))
    platforms_dir = plugins_dir / "platforms"
    cocoa_plugin = platforms_dir / "libqcocoa.dylib"
    if not cocoa_plugin.exists():
        raise RuntimeError(
            "Qt macOS platform plugin libqcocoa.dylib is missing. Recreate the "
            "virtual environment with Python 3.11 and reinstall requirements."
        )

    _prepend_env_path("QT_PLUGIN_PATH", plugins_dir)
    current_platform_path = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    current_cocoa_plugin = Path(current_platform_path) / "libqcocoa.dylib"
    if not current_platform_path or not current_cocoa_plugin.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_dir)


def _usable_qt_plugins_dir(plugins_dir: Path, pyside_version: str) -> Path:
    """Return a Qt plugin directory that macOS can load from a copied venv."""
    version_marker = f"pyside6-{pyside_version}"
    target = Path(tempfile.gettempdir()) / "ai-news-monitor-qt-plugins" / version_marker
    target_platform_plugin = target / "platforms" / "libqcocoa.dylib"
    try:
        if not target_platform_plugin.exists() and target.exists():
            shutil.rmtree(target)
        if not target_platform_plugin.exists():
            shutil.copytree(plugins_dir, target, symlinks=True)
        subprocess.run(
            ["chflags", "-R", "nohidden", str(target)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(["xattr", "-cr", str(target)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return plugins_dir

    if target_platform_plugin.exists():
        return target
    return plugins_dir


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "doctor":
        from src.doctor import main as doctor_main

        return doctor_main(argv[1:])

    try:
        assert_runtime_dependencies()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    runtime_dir = ensure_runtime_files()
    setup_logging(runtime_dir)
    logging.getLogger(__name__).info("AI News Monitor starting")

    try:
        _configure_qt_runtime()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    from PySide6.QtWidgets import QApplication

    from src.ui.main_window import MainWindow

    app = QApplication([sys.argv[0], *argv])
    app.setApplicationName("AI News Monitor")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(runtime_dir)
    window.show()
    exit_code = app.exec()
    logging.getLogger(__name__).info("AI News Monitor stopped")
    return int(exit_code)
