from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.i18n import text
from src.models import RuntimeStatus
from src.utils.time_utils import iso_or_empty


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.language = "en"
        self.start_button = QPushButton(text("start", self.language))
        self.pause_button = QPushButton(text("pause", self.language))
        self.resume_button = QPushButton(text("resume", self.language))
        self.stop_button = QPushButton(text("stop", self.language))
        self.test_notification_button = QPushButton(text("test_notification", self.language))

        self.labels: dict[str, QLabel] = {}
        self.stat_titles: dict[str, QLabel] = {}
        self.stat_cards: list[QFrame] = []
        self.action_buttons: list[QPushButton] = []
        self._stat_columns = 0
        self._action_columns = 0
        self.alert_list = QListWidget()
        self.log_list = QListWidget()
        self.health_list = QListWidget()
        self.gaps_list = QListWidget()

        for list_widget in (self.alert_list, self.log_list, self.health_list, self.gaps_list):
            list_widget.setWordWrap(True)
            list_widget.setAlternatingRowColors(True)
            list_widget.setMinimumHeight(150)
            list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        self.title_label = QLabel(text("app_title", self.language))
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)
        self.live_banner = QLabel(text("live_unconnected", self.language))
        self.live_banner.setObjectName("LiveBanner")
        self.live_banner.setWordWrap(True)
        layout.addWidget(self.live_banner)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        stats = [
            ("state", text("state", self.language)),
            ("active_topics_count", text("active_topics_count", self.language)),
            ("last_fetch_time", text("last_fetch_time", self.language)),
            ("last_successful_source_fetch", text("last_successful_source_fetch", self.language)),
            ("last_llm_analysis_time", text("last_llm_analysis_time", self.language)),
            ("last_alert_sent_time", text("last_alert_sent_time", self.language)),
            ("latest_articles_fetched", text("latest_articles_fetched", self.language)),
            ("latest_candidates", text("latest_candidates", self.language)),
            ("total_articles_processed", text("total_articles_processed", self.language)),
            ("queue_length", text("queue_length", self.language)),
            ("live_event_count", text("live_event_count", self.language)),
            ("alerts_sent_today", text("alerts_sent_today", self.language)),
            ("output_language", text("output_language", self.language)),
            ("alert_mode", text("alert_mode", self.language)),
            ("coverage_quality", text("coverage_quality", self.language)),
        ]
        for index, (key, label_text) in enumerate(stats):
            frame = QFrame()
            frame.setObjectName("StatCard")
            frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            card_layout = QVBoxLayout(frame)
            card_layout.setContentsMargins(12, 10, 12, 12)
            label = QLabel(label_text)
            label.setObjectName("StatLabel")
            label.setWordWrap(True)
            value = QLabel("-")
            value.setObjectName("StatValue")
            value.setWordWrap(True)
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            self.stat_titles[key] = label
            self.labels[key] = value
            self.stat_cards.append(frame)
            self.stats_grid.addWidget(frame, index // 5, index % 5)
        layout.addLayout(self.stats_grid)

        self.start_button.setObjectName("PrimaryButton")
        self.test_notification_button.setObjectName("SecondaryButton")
        self.pause_button.setObjectName("SecondaryButton")
        self.resume_button.setObjectName("SecondaryButton")
        self.stop_button.setObjectName("DangerButton")
        self.action_buttons = [
            self.start_button,
            self.test_notification_button,
            self.pause_button,
            self.resume_button,
            self.stop_button,
        ]
        self.actions_grid = QGridLayout()
        self.actions_grid.setSpacing(8)
        for index, button in enumerate(self.action_buttons):
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.actions_grid.addWidget(button, 0, index)
        layout.addLayout(self.actions_grid)

        self.body_splitter = QSplitter(Qt.Horizontal)
        self.body_splitter.setChildrenCollapsible(True)
        self.body_splitter.addWidget(self._feedback_panel("recent_alerts", self.alert_list))
        self.body_splitter.addWidget(self._feedback_panel("connection_health", self.health_list))
        self.body_splitter.addWidget(self._feedback_panel("intelligence_gaps", self.gaps_list))
        self.body_splitter.addWidget(self._feedback_panel("recent_logs", self.log_list))
        self.body_splitter.setStretchFactor(0, 2)
        self.body_splitter.setStretchFactor(1, 1)
        self.body_splitter.setStretchFactor(2, 1)
        self.body_splitter.setStretchFactor(3, 2)
        layout.addWidget(self.body_splitter, 2)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        self._apply_adaptive_layout()
        self.apply_language(self.language)

    def _feedback_panel(self, label_key: str, list_widget: QListWidget) -> QWidget:
        panel = QWidget()
        panel.setObjectName("FeedbackPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)
        label = QLabel(text(label_key, self.language))
        label.setObjectName("PanelTitle")
        label.setWordWrap(True)
        panel_layout.addWidget(label)
        panel_layout.addWidget(list_widget, 1)
        if label_key == "recent_alerts":
            self.recent_alerts_label = label
        elif label_key == "connection_health":
            self.health_label = label
        elif label_key == "intelligence_gaps":
            self.gaps_label = label
        elif label_key == "recent_logs":
            self.recent_logs_label = label
        return panel

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._apply_adaptive_layout()

    def _apply_adaptive_layout(self) -> None:
        viewport_width = self.scroll.viewport().width()
        width = viewport_width if viewport_width > 0 else self.width()
        self._set_stat_columns(_dashboard_columns(width))
        self._set_action_columns(_action_columns(width))
        narrow = width < 760
        orientation = Qt.Vertical if narrow else Qt.Horizontal
        if self.body_splitter.orientation() != orientation:
            self.body_splitter.setOrientation(orientation)
            if narrow:
                self.body_splitter.setSizes([180, 150, 150, 180])
            else:
                self.body_splitter.setSizes([320, 220, 220, 320])

    def _set_stat_columns(self, columns: int) -> None:
        if columns == self._stat_columns:
            return
        self._stat_columns = columns
        for card in self.stat_cards:
            self.stats_grid.removeWidget(card)
        for index, card in enumerate(self.stat_cards):
            self.stats_grid.addWidget(card, index // columns, index % columns)

    def _set_action_columns(self, columns: int) -> None:
        if columns == self._action_columns:
            return
        self._action_columns = columns
        for button in self.action_buttons:
            self.actions_grid.removeWidget(button)
        for index, button in enumerate(self.action_buttons):
            self.actions_grid.addWidget(button, index // columns, index % columns)

    def apply_language(self, language: str) -> None:
        self.language = language
        self.title_label.setText(text("app_title", language))
        self.start_button.setText(text("start", language))
        self.pause_button.setText(text("pause", language))
        self.resume_button.setText(text("resume", language))
        self.stop_button.setText(text("stop", language))
        self.test_notification_button.setText(text("test_notification", language))
        self.recent_alerts_label.setText(text("recent_alerts", language))
        self.recent_logs_label.setText(text("recent_logs", language))
        self.health_label.setText(text("connection_health", language))
        self.gaps_label.setText(text("intelligence_gaps", language))
        for key, label in self.stat_titles.items():
            label.setText(text(key, language))
        if "/events" not in self.live_banner.text():
            self.live_banner.setText(text("live_unconnected", language))

    def update_status(self, status: RuntimeStatus) -> None:
        values = {
            "state": status.state,
            "active_topics_count": str(status.active_topics_count),
            "last_fetch_time": iso_or_empty(status.last_fetch_time) or "-",
            "last_successful_source_fetch": iso_or_empty(status.last_successful_source_fetch) or "-",
            "last_llm_analysis_time": iso_or_empty(status.last_llm_analysis_time) or "-",
            "last_alert_sent_time": iso_or_empty(status.last_alert_sent_time) or "-",
            "latest_articles_fetched": str(status.latest_articles_fetched),
            "latest_candidates": str(status.latest_candidates),
            "total_articles_processed": str(status.total_articles_processed),
            "queue_length": str(status.queue_length),
            "live_event_count": str(status.live_event_count),
            "alerts_sent_today": str(status.alerts_sent_today),
            "output_language": status.output_language,
            "alert_mode": status.alert_mode,
            "coverage_quality": status.coverage_quality.get("global", {}).get("coverage_quality", "-"),
        }
        for key, value in values.items():
            self.labels[key].setText(value)
        if status.local_server_url:
            self.live_banner.setText(text("live_service_url", self.language, url=f"{status.local_server_url}/events"))
        else:
            self.live_banner.setText(text("live_off", self.language))
        self.alert_list.clear()
        for alert in status.recent_alerts:
            self.alert_list.addItem(f"[{alert.analysis.relevance_score}] {alert.topic_name} - {alert.article.title}")
        self.log_list.clear()
        for item in status.recent_logs[:50]:
            self.log_list.addItem(item)
        self.health_list.clear()
        merged_health = {**status.source_health, **status.notifier_health}
        for name, value in merged_health.items():
            self.health_list.addItem(f"{name}: {value}")
        for name, state in {**status.source_states, **status.notifier_states}.items():
            if name not in merged_health:
                health = state.get("health") or ("enabled" if state.get("enabled") else "disabled")
                self.health_list.addItem(f"{name}: {health}")
        self.gaps_list.clear()
        for item in status.intelligence_gaps.get("critical_gaps", [])[:5]:
            self.gaps_list.addItem(f"{item.get('name')}: {item.get('reason')}")
        for item in status.intelligence_gaps.get("degraded_groups", [])[:5]:
            self.gaps_list.addItem(f"{item.get('name')}: {item.get('reason')}")
        self.pause_button.setEnabled(status.state == "Running")
        self.resume_button.setEnabled(status.state == "Paused")
        self.stop_button.setEnabled(status.state in {"Running", "Paused", "Error"})
        self.start_button.setEnabled(status.state in {"Stopped", "Error"})


def _dashboard_columns(width: int) -> int:
    if width >= 1120:
        return 5
    if width >= 900:
        return 4
    if width >= 660:
        return 3
    if width >= 430:
        return 2
    return 1


def _action_columns(width: int) -> int:
    if width >= 860:
        return 5
    if width >= 560:
        return 3
    if width >= 360:
        return 2
    return 1
