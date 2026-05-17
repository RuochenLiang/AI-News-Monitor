from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigError, load_config, save_config, validate_topic
from src.i18n import text
from src.models import TopicConfig
from src.ui.widgets import show_error, show_info


class TopicsPage(QWidget):
    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.current_index = -1
        self.language = self.config.app.output_language

        self.topic_list = QListWidget()
        self.new_button = QPushButton(text("new", self.language))
        self.save_button = QPushButton(text("save", self.language))
        self.delete_button = QPushButton(text("delete", self.language))
        self.toggle_button = QPushButton(text("toggle", self.language))

        self.name = QLineEdit()
        self.enabled = QCheckBox(text("enabled", self.language))
        self.broad_search = QCheckBox(text("allow_broad_search", self.language))
        self.prompt = QTextEdit()
        self.keywords = QTextEdit()
        self.related_stocks = QTextEdit()
        self.output_language = QLineEdit("zh-CN")
        self.threshold = QSpinBox()
        self.threshold.setRange(0, 100)
        self.threshold.setValue(80)
        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(0, 86400)
        self.poll_interval.setSpecialValueText(text("default", self.language))
        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 10080)
        self.cooldown.setSpecialValueText(text("none", self.language))
        self.official_urls = QTextEdit()

        self._build_layout()
        self._connect()
        self.reload()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        self.title_label = QLabel(text("topics_title", self.language))
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)

        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.topic_list)
        left_buttons = QHBoxLayout()
        for button in (self.new_button, self.delete_button, self.toggle_button):
            left_buttons.addWidget(button)
        left_layout.addLayout(left_buttons)

        right = QWidget()
        form = QFormLayout(right)
        self.row_labels: dict[str, QLabel] = {}
        form.addRow(self._row_label("topic_name"), self.name)
        form.addRow("", self.enabled)
        form.addRow("", self.broad_search)
        form.addRow(self._row_label("topic_prompt"), self.prompt)
        form.addRow(self._row_label("topic_keywords"), self.keywords)
        form.addRow(self._row_label("topic_watchlist"), self.related_stocks)
        form.addRow(self._row_label("topic_output_language"), self.output_language)
        form.addRow(self._row_label("topic_min_relevance"), self.threshold)
        form.addRow(self._row_label("topic_poll_interval"), self.poll_interval)
        form.addRow(self._row_label("topic_cooldown"), self.cooldown)
        form.addRow(self._row_label("topic_official_rss"), self.official_urls)
        form.addRow("", self.save_button)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([250, 700])
        layout.addWidget(splitter, 1)

    def _connect(self) -> None:
        self.topic_list.currentRowChanged.connect(self._load_selected)
        self.new_button.clicked.connect(self._new_topic)
        self.save_button.clicked.connect(self._save_current)
        self.delete_button.clicked.connect(self._delete_current)
        self.toggle_button.clicked.connect(self._toggle_current)

    def reload(self) -> None:
        self.config = load_config(self.config_path)
        self.topic_list.clear()
        for topic in self.config.topics:
            prefix = "*" if topic.enabled else "-"
            self.topic_list.addItem(f"{prefix} {topic.name}")
        if self.config.topics:
            self.topic_list.setCurrentRow(0)
        else:
            self._new_topic()

    def _load_selected(self, index: int) -> None:
        self.current_index = index
        if index < 0 or index >= len(self.config.topics):
            return
        topic = self.config.topics[index]
        self.name.setText(topic.name)
        self.enabled.setChecked(topic.enabled)
        self.broad_search.setChecked(topic.broad_search)
        self.prompt.setPlainText(topic.prompt)
        self.keywords.setPlainText("\n".join(topic.keywords))
        self.related_stocks.setPlainText("\n".join(topic.related_stocks))
        self.output_language.setText(topic.output_language)
        self.threshold.setValue(topic.min_relevance_score)
        self.poll_interval.setValue(topic.poll_interval_seconds or 0)
        self.cooldown.setValue(topic.cooldown_minutes or 0)
        self.official_urls.setPlainText("\n".join(topic.official_rss_urls))

    def _new_topic(self) -> None:
        self.current_index = -1
        self.name.clear()
        self.enabled.setChecked(True)
        self.broad_search.setChecked(False)
        self.prompt.clear()
        self.keywords.clear()
        self.related_stocks.clear()
        self.output_language.setText("zh-CN")
        self.threshold.setValue(80)
        self.poll_interval.setValue(0)
        self.cooldown.setValue(0)
        self.official_urls.clear()

    def _save_current(self) -> None:
        try:
            topic = self._topic_from_form()
            validate_topic(topic)
            if self.current_index < 0:
                self.config.topics.append(topic)
            else:
                self.config.topics[self.current_index] = topic
            save_config(self.config, self.config_path)
            show_info(self, text("saved_title", self.language), text("topic_saved_message", self.language))
            self.reload()
        except ConfigError as exc:
            show_error(self, text("topic_invalid_title", self.language), str(exc))

    def _delete_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.config.topics):
            return
        answer = QMessageBox.question(
            self,
            text("confirm_delete_title", self.language),
            text("confirm_delete_topic", self.language),
        )
        if answer == QMessageBox.Yes:
            del self.config.topics[self.current_index]
            save_config(self.config, self.config_path)
            self.reload()

    def _toggle_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.config.topics):
            return
        self.config.topics[self.current_index].enabled = not self.config.topics[self.current_index].enabled
        save_config(self.config, self.config_path)
        self.reload()

    def apply_language(self, language: str) -> None:
        self.language = language
        self.title_label.setText(text("topics_title", language))
        self.new_button.setText(text("new", language))
        self.save_button.setText(text("save", language))
        self.delete_button.setText(text("delete", language))
        self.toggle_button.setText(text("toggle", language))
        self.enabled.setText(text("enabled", language))
        self.broad_search.setText(text("allow_broad_search", language))
        self.poll_interval.setSpecialValueText(text("default", language))
        self.cooldown.setSpecialValueText(text("none", language))
        for key, label in self.row_labels.items():
            label.setText(text(key, language))

    def _row_label(self, key: str) -> QLabel:
        label = QLabel(text(key, self.language))
        self.row_labels[key] = label
        return label

    def _topic_from_form(self) -> TopicConfig:
        return TopicConfig(
            name=self.name.text().strip(),
            enabled=self.enabled.isChecked(),
            broad_search=self.broad_search.isChecked(),
            prompt=self.prompt.toPlainText().strip(),
            keywords=_lines(self.keywords.toPlainText()),
            related_stocks=_lines(self.related_stocks.toPlainText()),
            output_language=self.output_language.text().strip() or "zh-CN",
            min_relevance_score=self.threshold.value(),
            poll_interval_seconds=self.poll_interval.value() or None,
            cooldown_minutes=self.cooldown.value() or None,
            official_rss_urls=_lines(self.official_urls.toPlainText()),
        )


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
