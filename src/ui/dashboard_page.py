from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
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
        self.alert_list = QListWidget()
        self.log_list = QListWidget()

        layout = QVBoxLayout(self)
        self.title_label = QLabel(text("app_title", self.language))
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)
        self.live_banner = QLabel(text("live_unconnected", self.language))
        self.live_banner.setObjectName("LiveBanner")
        layout.addWidget(self.live_banner)

        grid = QGridLayout()
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
            card_layout = QVBoxLayout(frame)
            label = QLabel(label_text)
            value = QLabel("-")
            value.setObjectName("StatValue")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            self.stat_titles[key] = label
            self.labels[key] = value
            grid.addWidget(frame, index // 3, index % 3)
        layout.addLayout(grid)

        buttons = QHBoxLayout()
        for button in (
            self.start_button,
            self.pause_button,
            self.resume_button,
            self.stop_button,
            self.test_notification_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        body = QHBoxLayout()
        alerts_panel = QVBoxLayout()
        self.recent_alerts_label = QLabel(text("recent_alerts", self.language))
        alerts_panel.addWidget(self.recent_alerts_label)
        alerts_panel.addWidget(self.alert_list)
        health_panel = QVBoxLayout()
        self.health_label = QLabel(text("connection_health", self.language))
        health_panel.addWidget(self.health_label)
        self.health_list = QListWidget()
        health_panel.addWidget(self.health_list)
        gaps_panel = QVBoxLayout()
        self.gaps_label = QLabel(text("intelligence_gaps", self.language))
        gaps_panel.addWidget(self.gaps_label)
        self.gaps_list = QListWidget()
        gaps_panel.addWidget(self.gaps_list)
        logs_panel = QVBoxLayout()
        self.recent_logs_label = QLabel(text("recent_logs", self.language))
        logs_panel.addWidget(self.recent_logs_label)
        logs_panel.addWidget(self.log_list)
        body.addLayout(alerts_panel, 1)
        body.addLayout(health_panel, 1)
        body.addLayout(gaps_panel, 1)
        body.addLayout(logs_panel, 1)
        layout.addLayout(body, 1)
        self.apply_language(self.language)

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
            self.live_banner.setText(f"Live service: {status.local_server_url}/events")
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
