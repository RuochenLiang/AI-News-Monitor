from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QMainWindow,
    QMenu,
    QSystemTrayIcon,
    QTabWidget,
)

from src.config import load_config
from src.i18n import text
from src.scheduler import MonitorWorker
from src.ui.dashboard_page import DashboardPage
from src.ui.logs_page import LogsPage
from src.ui.settings_page import SettingsPage
from src.ui.topics_page import TopicsPage


class UiBridge(QObject):
    status_updated = Signal(object)
    log_updated = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, runtime_dir: Path):
        super().__init__()
        self.runtime_dir = runtime_dir
        self.config_path = runtime_dir / "config.yaml"
        self.bridge = UiBridge()
        self.worker = MonitorWorker(
            self.config_path,
            runtime_dir,
            status_callback=self.bridge.status_updated.emit,
            log_callback=self.bridge.log_updated.emit,
        )
        self.dashboard = DashboardPage()
        self.topics = TopicsPage(self.config_path)
        self.settings = SettingsPage(self.config_path, runtime_dir)
        self.logs = LogsPage(runtime_dir)
        self.tabs = QTabWidget()
        self.tray: QSystemTrayIcon | None = None
        self.tray_actions: dict[str, QAction] = {}
        self.language = load_config(self.config_path).app.output_language

        self._build()
        self._connect()
        self._setup_tray()
        self._apply_style()
        self._apply_language(self.language)
        self.worker.start_event_server()
        self.dashboard.update_status(self.worker.status)

    def _build(self) -> None:
        self.setWindowTitle(text("app_title", self.language))
        self.resize(1180, 760)
        self.setMinimumSize(560, 420)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.addTab(self.dashboard, text("dashboard", self.language))
        self.tabs.addTab(self.topics, text("topics", self.language))
        self.tabs.addTab(self.settings, text("settings", self.language))
        self.tabs.addTab(self.logs, text("logs", self.language))
        self.setCentralWidget(self.tabs)

    def _connect(self) -> None:
        self.dashboard.start_button.clicked.connect(self.worker.start)
        self.dashboard.pause_button.clicked.connect(self.worker.pause)
        self.dashboard.resume_button.clicked.connect(self.worker.resume)
        self.dashboard.stop_button.clicked.connect(self.worker.stop)
        self.dashboard.test_notification_button.clicked.connect(self._send_test_notifications)
        self.bridge.status_updated.connect(self.dashboard.update_status)
        self.bridge.log_updated.connect(self.logs.append_log)
        self.settings.bridge.language_changed.connect(self._apply_language)
        self.tabs.currentChanged.connect(self._animate_tab)

    def _apply_language(self, language: str) -> None:
        self.language = language
        self.setWindowTitle(text("app_title", language))
        self.tabs.setTabText(0, text("dashboard", language))
        self.tabs.setTabText(1, text("topics", language))
        self.tabs.setTabText(2, text("settings", language))
        self.tabs.setTabText(3, text("logs", language))
        self.dashboard.apply_language(language)
        self.topics.apply_language(language)
        self.settings.apply_language(language)
        self.logs.apply_language(language)
        for key, action in self.tray_actions.items():
            action.setText(text(key, language))
        if self.tray:
            self.tray.setToolTip(text("app_title", language))
        self.worker.reload_runtime_settings()

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon.fromTheme("view-refresh"), self)
        menu = QMenu()
        show_action = QAction(text("show_window", self.language), self)
        pause_action = QAction(text("pause", self.language), self)
        resume_action = QAction(text("resume", self.language), self)
        stop_action = QAction(text("stop", self.language), self)
        quit_action = QAction(text("quit", self.language), self)
        self.tray_actions = {
            "show_window": show_action,
            "pause": pause_action,
            "resume": resume_action,
            "stop": stop_action,
            "quit": quit_action,
        }
        show_action.triggered.connect(self.showNormal)
        pause_action.triggered.connect(self.worker.pause)
        resume_action.triggered.connect(self.worker.resume)
        stop_action.triggered.connect(self.worker.stop)
        quit_action.triggered.connect(self._quit)
        for action in (show_action, pause_action, resume_action, stop_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("AI News Monitor")
        self.tray.show()

    def _send_test_notifications(self) -> None:
        self.settings.run_enabled_notification_tests()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray and self.settings.run_minimized_to_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray.showMessage("AI News Monitor", text("live_running_background", self.language))
            return
        self.worker.stop()
        event.accept()
        QTimer.singleShot(0, QApplication.quit)

    def _quit(self) -> None:
        self.worker.stop()
        QApplication.quit()

    def _apply_style(self) -> None:
        QApplication.instance().setFont(QFont("-apple-system, BlinkMacSystemFont, SF Pro Text, Inter", 14))
        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                color: #172033;
                selection-background-color: #2563eb;
            }
            QMainWindow, QTabWidget::pane {
                background: #eef5f2;
                border: 0;
            }
            QTabWidget, QSplitter, QScrollArea, QScrollArea > QWidget > QWidget {
                background: #eef5f2;
            }
            #PageTitle {
                font-size: 26px;
                font-weight: 650;
                margin: 14px 0 18px 0;
            }
            #StatCard, #FeedbackPanel, QGroupBox {
                background: #fbfcfd;
                border: 1px solid #d6e2df;
                border-radius: 8px;
                margin-top: 12px;
                padding: 14px;
            }
            #StatCard {
                border-left: 4px solid #5ba7a1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #506176;
                font-weight: 600;
            }
            #StatLabel, #PanelTitle {
                color: #506176;
                font-weight: 650;
            }
            #StatValue {
                font-size: 18px;
                font-weight: 650;
                color: #142033;
            }
            #LiveBanner {
                background: #e7f3f0;
                border: 1px solid #acd2cb;
                border-radius: 8px;
                padding: 10px 12px;
                color: #0f5d57;
                font-weight: 600;
            }
            QPushButton {
                background: #2563eb;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 9px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton#SecondaryButton {
                background: #f7faf9;
                color: #172033;
                border: 1px solid #cad8d5;
            }
            QPushButton#SecondaryButton:hover {
                background: #e7f3f0;
                border-color: #5ba7a1;
            }
            QPushButton#DangerButton {
                background: #b42318;
            }
            QPushButton#DangerButton:hover {
                background: #912018;
            }
            QPushButton:disabled {
                background: #c6d1d5;
                color: #5d697d;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {
                background: #ffffff;
                border: 1px solid #cfd9e2;
                border-radius: 8px;
                padding: 8px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QListWidget:focus {
                border: 1px solid #2563eb;
            }
            QScrollArea {
                border: 0;
                background: #eef5f2;
            }
            QListWidget::item {
                border-bottom: 1px solid #edf2f5;
                padding: 7px;
            }
            QTabBar::tab {
                padding: 12px 20px;
                color: #506176;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                font-weight: 650;
                color: #172033;
                border-bottom: 2px solid #0f766e;
                background: #fbfcfd;
            }
            """)

    def _animate_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if not widget:
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", widget)
        animation.setDuration(120)
        animation.setStartValue(0.86)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        animation.start(QPropertyAnimation.DeleteWhenStopped)
