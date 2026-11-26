from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigError, load_config, save_config, validate_topic
from src.i18n import text
from src.models import TopicConfig
from src.sources.source_preview import topic_source_preview_lines
from src.ui.widgets import show_error, show_info


class TopicsPage(QWidget):
    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.current_index = -1
        self.language = self.config.app.output_language
        self._loading = False
        self._dirty = False

        self.topic_list = QListWidget()
        self.topic_search = QLineEdit()
        self.topic_search.setPlaceholderText(text("topic_search_placeholder", self.language))
        self.enabled_filter = QCheckBox(text("topic_enabled_only", self.language))
        self.topic_list_summary = QLabel()
        self.editor_status = QLabel()
        self.new_button = QPushButton(text("new", self.language))
        self.save_button = QPushButton(text("save", self.language))
        self.delete_button = QPushButton(text("delete", self.language))
        self.toggle_button = QPushButton(text("toggle", self.language))

        self.name = QLineEdit()
        self.topic_id = QLineEdit()
        self.enabled = QCheckBox(text("enabled", self.language))
        self.broad_search = QCheckBox(text("allow_broad_search", self.language))
        self.social_enabled = QCheckBox(text("topic_social_enabled", self.language))
        self.include_timeline = QCheckBox(text("topic_include_timeline", self.language))
        self.include_source_comparison = QCheckBox(text("topic_include_source_comparison", self.language))
        self.include_user_action = QCheckBox(text("topic_include_user_action", self.language))
        self.prompt = QTextEdit()
        self.keywords = QTextEdit()
        self.related_stocks = QTextEdit()
        self.output_language = QLineEdit("zh-CN")
        self.source_mode = QComboBox()
        self.source_mode.addItems(["manual", "auto", "hybrid"])
        self.domains = QTextEdit()
        self.preferred_regions = QTextEdit()
        self.threshold = QSpinBox()
        self.threshold.setRange(0, 100)
        self.threshold.setValue(80)
        self.confidence_threshold = QDoubleSpinBox()
        self.confidence_threshold.setRange(0.0, 1.0)
        self.confidence_threshold.setDecimals(2)
        self.confidence_threshold.setSingleStep(0.05)
        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(0, 86400)
        self.poll_interval.setSpecialValueText(text("default", self.language))
        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 10080)
        self.cooldown.setSpecialValueText(text("none", self.language))
        self.official_urls = QTextEdit()
        self.preview_sources_button = QPushButton(text("preview_source_selection", self.language))
        self.source_preview = QTextEdit()
        self.source_preview.setReadOnly(True)
        for editor in (
            self.prompt,
            self.keywords,
            self.related_stocks,
            self.domains,
            self.preferred_regions,
            self.official_urls,
            self.source_preview,
        ):
            editor.setLineWrapMode(QTextEdit.WidgetWidth)
        self.prompt.setMinimumHeight(120)
        self.source_preview.setMinimumHeight(150)

        self._build_layout()
        self._connect()
        self.reload()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        self.title_label = QLabel(text("topics_title", self.language))
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        left = QWidget()
        left.setMinimumWidth(0)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.topic_search)
        left_layout.addWidget(self.enabled_filter)
        left_layout.addWidget(self.topic_list)
        self.topic_list_summary.setObjectName("StatLabel")
        left_layout.addWidget(self.topic_list_summary)
        left_buttons = QHBoxLayout()
        for button in (self.new_button, self.delete_button, self.toggle_button):
            left_buttons.addWidget(button)
        left_layout.addLayout(left_buttons)

        self.row_labels: dict[str, QLabel] = {}
        right = QWidget()
        right.setMinimumWidth(0)
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.topic_tabs = QTabWidget()
        self.topic_tabs.addTab(self._scroll_tab(self._definition_form()), text("topic_tab_definition", self.language))
        self.topic_tabs.addTab(self._scroll_tab(self._source_form()), text("topic_tab_sources", self.language))
        self.topic_tabs.addTab(self._scroll_tab(self._report_form()), text("topic_tab_report", self.language))
        right_layout.addWidget(self.topic_tabs, 1)
        footer = QHBoxLayout()
        self.editor_status.setObjectName("StatLabel")
        footer.addWidget(self.editor_status, 1)
        footer.addStretch(1)
        self.save_button.setObjectName("PrimaryButton")
        footer.addWidget(self.save_button)
        right_layout.addLayout(footer)

        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setSizes([250, 700])
        layout.addWidget(self.splitter, 1)
        self._apply_adaptive_layout()

    def _definition_form(self) -> QWidget:
        tab = QWidget()
        form = self._form_layout(tab)
        form.addRow(self._row_label("topic_name"), self.name)
        form.addRow(self._row_label("topic_id"), self.topic_id)
        form.addRow("", self.enabled)
        form.addRow(self._row_label("topic_prompt"), self.prompt)
        form.addRow(self._row_label("topic_keywords"), self.keywords)
        form.addRow(self._row_label("topic_watchlist"), self.related_stocks)
        form.addRow(self._row_label("topic_output_language"), self.output_language)
        return tab

    def _source_form(self) -> QWidget:
        tab = QWidget()
        form = self._form_layout(tab)
        form.addRow("", self.broad_search)
        form.addRow("", self.social_enabled)
        form.addRow(self._row_label("topic_source_mode"), self.source_mode)
        form.addRow(self._row_label("topic_domains"), self.domains)
        form.addRow(self._row_label("topic_preferred_regions"), self.preferred_regions)
        form.addRow(self._row_label("topic_official_rss"), self.official_urls)
        form.addRow("", self.preview_sources_button)
        form.addRow(self._row_label("topic_source_preview"), self.source_preview)
        return tab

    def _report_form(self) -> QWidget:
        tab = QWidget()
        form = self._form_layout(tab)
        form.addRow(self._row_label("topic_min_relevance"), self.threshold)
        form.addRow(self._row_label("topic_min_confidence"), self.confidence_threshold)
        form.addRow(self._row_label("topic_poll_interval"), self.poll_interval)
        form.addRow(self._row_label("topic_cooldown"), self.cooldown)
        form.addRow("", self.include_timeline)
        form.addRow("", self.include_source_comparison)
        form.addRow("", self.include_user_action)
        return tab

    def _form_layout(self, parent: QWidget) -> QFormLayout:
        form = QFormLayout(parent)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        return form

    def _scroll_tab(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll.setWidget(content)
        return scroll

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._apply_adaptive_layout()

    def _apply_adaptive_layout(self) -> None:
        narrow = self.width() < 760
        orientation = Qt.Vertical if narrow else Qt.Horizontal
        if self.splitter.orientation() == orientation:
            return
        self.splitter.setOrientation(orientation)
        self.splitter.setSizes([220, 520] if narrow else [250, 700])

    def _connect(self) -> None:
        self.topic_list.currentRowChanged.connect(self._load_selected)
        self.topic_search.textChanged.connect(
            lambda _value: self._render_topic_list(self.current_index, load_selection=False)
        )
        self.enabled_filter.toggled.connect(
            lambda _checked: self._render_topic_list(self.current_index, load_selection=False)
        )
        self.new_button.clicked.connect(self._new_topic)
        self.save_button.clicked.connect(self._save_current)
        self.preview_sources_button.clicked.connect(self._preview_source_selection)
        self.delete_button.clicked.connect(self._delete_current)
        self.toggle_button.clicked.connect(self._toggle_current)
        self._connect_dirty_tracking()

    def _connect_dirty_tracking(self) -> None:
        for field in (self.name, self.topic_id, self.output_language):
            field.textChanged.connect(self._mark_dirty)
        for editor in (
            self.prompt,
            self.keywords,
            self.related_stocks,
            self.domains,
            self.preferred_regions,
            self.official_urls,
        ):
            editor.textChanged.connect(self._mark_dirty)
        for checkbox in (
            self.enabled,
            self.broad_search,
            self.social_enabled,
            self.include_timeline,
            self.include_source_comparison,
            self.include_user_action,
        ):
            checkbox.toggled.connect(self._mark_dirty)
        self.source_mode.currentTextChanged.connect(self._mark_dirty)
        self.threshold.valueChanged.connect(self._mark_dirty)
        self.confidence_threshold.valueChanged.connect(self._mark_dirty)
        self.poll_interval.valueChanged.connect(self._mark_dirty)
        self.cooldown.valueChanged.connect(self._mark_dirty)

    def reload(self, select_index: int | None = None) -> None:
        self.config = load_config(self.config_path)
        if self.config.topics:
            self._render_topic_list(0 if select_index is None else select_index)
        else:
            self._new_topic()

    def _render_topic_list(self, select_index: int | None = None, *, load_selection: bool = True) -> None:
        selected_index = self.current_index if select_index is None else select_index
        visible_indexes: list[int] = []
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        for index, topic in enumerate(self.config.topics):
            if not self._topic_matches_filter(topic):
                continue
            item = QListWidgetItem(self._topic_item_text(topic))
            item.setData(Qt.UserRole, index)
            item.setToolTip(topic.prompt)
            self.topic_list.addItem(item)
            visible_indexes.append(index)
        self.topic_list.blockSignals(False)

        if selected_index in visible_indexes:
            row = visible_indexes.index(selected_index)
            if load_selection:
                self.topic_list.setCurrentRow(row)
            else:
                self.topic_list.blockSignals(True)
                self.topic_list.setCurrentRow(row)
                self.topic_list.blockSignals(False)
        elif visible_indexes and not (selected_index is not None and 0 <= selected_index < len(self.config.topics)):
            if load_selection:
                self.topic_list.setCurrentRow(0)
            else:
                self.topic_list.blockSignals(True)
                self.topic_list.clearSelection()
                self.topic_list.blockSignals(False)
        else:
            self.topic_list.blockSignals(True)
            self.topic_list.clearSelection()
            self.topic_list.blockSignals(False)
            if selected_index is not None and 0 <= selected_index < len(self.config.topics):
                self.current_index = selected_index
            self._update_controls()
        self._update_list_summary(len(visible_indexes))
        if not load_selection:
            self._update_controls()

    def _topic_matches_filter(self, topic: TopicConfig) -> bool:
        if self.enabled_filter.isChecked() and not topic.enabled:
            return False
        query = self.topic_search.text().strip().casefold()
        if not query:
            return True
        haystack = " ".join(
            [
                topic.name,
                topic.id or "",
                topic.prompt,
                " ".join(topic.keywords),
                " ".join(topic.domains),
                " ".join(topic.preferred_regions),
            ]
        ).casefold()
        return query in haystack

    def _topic_item_text(self, topic: TopicConfig) -> str:
        status = "●" if topic.enabled else "○"
        details = [
            topic.id or text("topic_no_id", self.language),
            topic.source_mode,
            text("topic_keyword_count", self.language, count=len(topic.keywords)),
        ]
        return f"{status} {topic.name}\n{' · '.join(details)}"

    def _load_selected(self, row: int) -> None:
        item = self.topic_list.item(row) if row >= 0 else None
        index = item.data(Qt.UserRole) if item else -1
        target_index = int(index) if isinstance(index, int) else -1
        if target_index < 0 or target_index >= len(self.config.topics):
            self._update_controls()
            return
        if target_index != self.current_index and not self._confirm_navigation():
            self._select_list_index(self.current_index)
            return
        self._load_topic_at_index(target_index)

    def _load_topic_at_index(self, index: int) -> None:
        self.current_index = index
        topic = self.config.topics[index]
        self._loading = True
        self.name.setText(topic.name)
        self.topic_id.setText(topic.id or "")
        self.enabled.setChecked(topic.enabled)
        self.broad_search.setChecked(topic.broad_search)
        self.social_enabled.setChecked(topic.social_enabled)
        self.prompt.setPlainText(topic.prompt)
        self.keywords.setPlainText("\n".join(topic.keywords))
        self.related_stocks.setPlainText("\n".join(topic.related_stocks))
        self.output_language.setText(topic.output_language)
        self.source_mode.setCurrentText(topic.source_mode)
        self.domains.setPlainText("\n".join(topic.domains))
        self.preferred_regions.setPlainText("\n".join(topic.preferred_regions))
        self.threshold.setValue(topic.min_relevance_score)
        self.confidence_threshold.setValue(topic.min_confidence_score)
        self.poll_interval.setValue(topic.poll_interval_seconds or 0)
        self.cooldown.setValue(topic.cooldown_minutes or 0)
        self.official_urls.setPlainText("\n".join(topic.official_rss_urls))
        self.include_timeline.setChecked(topic.report_include_timeline)
        self.include_source_comparison.setChecked(topic.report_include_source_comparison)
        self.include_user_action.setChecked(topic.report_include_user_action)
        self.source_preview.clear()
        self._loading = False
        self._set_dirty(False)

    def _new_topic(self) -> None:
        if not self._confirm_navigation():
            return
        self.topic_list.blockSignals(True)
        self.topic_list.clearSelection()
        self.topic_list.blockSignals(False)
        self.current_index = -1
        self._loading = True
        self.name.clear()
        self.topic_id.clear()
        self.enabled.setChecked(True)
        self.broad_search.setChecked(False)
        self.social_enabled.setChecked(False)
        self.prompt.clear()
        self.keywords.clear()
        self.related_stocks.clear()
        self.output_language.setText("zh-CN")
        self.source_mode.setCurrentText("manual")
        self.domains.clear()
        self.preferred_regions.clear()
        self.threshold.setValue(80)
        self.confidence_threshold.setValue(0.0)
        self.poll_interval.setValue(0)
        self.cooldown.setValue(0)
        self.official_urls.clear()
        self.include_timeline.setChecked(True)
        self.include_source_comparison.setChecked(True)
        self.include_user_action.setChecked(True)
        self.source_preview.clear()
        self._loading = False
        self._update_list_summary()
        self._set_dirty(True)

    def _save_current(self, silent: bool = False) -> bool:
        try:
            topic = self._topic_from_form()
            validate_topic(topic)
            if self.current_index < 0:
                target_index = len(self.config.topics)
                self.config.topics.append(topic)
            else:
                target_index = self.current_index
                self.config.topics[self.current_index] = topic
            save_config(self.config, self.config_path)
            self._set_dirty(False)
            if not silent:
                show_info(self, text("saved_title", self.language), text("topic_saved_message", self.language))
            self.reload(target_index)
            return True
        except ConfigError as exc:
            show_error(self, text("topic_invalid_title", self.language), str(exc))
            return False

    def _delete_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.config.topics):
            return
        if not self._confirm_navigation():
            return
        answer = QMessageBox.question(
            self,
            text("confirm_delete_title", self.language),
            text("confirm_delete_topic", self.language),
        )
        if answer == QMessageBox.Yes:
            del self.config.topics[self.current_index]
            next_index = min(self.current_index, len(self.config.topics) - 1)
            save_config(self.config, self.config_path)
            self._set_dirty(False)
            self.reload(next_index if next_index >= 0 else None)

    def _toggle_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.config.topics):
            return
        if not self._confirm_navigation():
            return
        self.config.topics[self.current_index].enabled = not self.config.topics[self.current_index].enabled
        self._loading = True
        self.enabled.setChecked(self.config.topics[self.current_index].enabled)
        self._loading = False
        save_config(self.config, self.config_path)
        self._set_dirty(False)
        self.reload(self.current_index)

    def apply_language(self, language: str) -> None:
        self.language = language
        self.title_label.setText(text("topics_title", language))
        self.topic_search.setPlaceholderText(text("topic_search_placeholder", language))
        self.enabled_filter.setText(text("topic_enabled_only", language))
        self.new_button.setText(text("new", language))
        self.save_button.setText(text("save", language))
        self.delete_button.setText(text("delete", language))
        self.toggle_button.setText(text("toggle", language))
        self.preview_sources_button.setText(text("preview_source_selection", language))
        if hasattr(self, "topic_tabs"):
            self.topic_tabs.setTabText(0, text("topic_tab_definition", language))
            self.topic_tabs.setTabText(1, text("topic_tab_sources", language))
            self.topic_tabs.setTabText(2, text("topic_tab_report", language))
        self.enabled.setText(text("enabled", language))
        self.broad_search.setText(text("allow_broad_search", language))
        self.social_enabled.setText(text("topic_social_enabled", language))
        self.include_timeline.setText(text("topic_include_timeline", language))
        self.include_source_comparison.setText(text("topic_include_source_comparison", language))
        self.include_user_action.setText(text("topic_include_user_action", language))
        self.poll_interval.setSpecialValueText(text("default", language))
        self.cooldown.setSpecialValueText(text("none", language))
        for key, label in self.row_labels.items():
            label.setText(text(key, language))
        self._render_topic_list(self.current_index, load_selection=False)
        self._update_controls()

    def _row_label(self, key: str) -> QLabel:
        label = QLabel(text(key, self.language))
        self.row_labels[key] = label
        return label

    def _topic_from_form(self) -> TopicConfig:
        return TopicConfig(
            id=self.topic_id.text().strip() or None,
            name=self.name.text().strip(),
            enabled=self.enabled.isChecked(),
            broad_search=self.broad_search.isChecked(),
            prompt=self.prompt.toPlainText().strip(),
            keywords=_lines(self.keywords.toPlainText()),
            related_stocks=_lines(self.related_stocks.toPlainText()),
            output_language=self.output_language.text().strip() or "zh-CN",
            source_mode=self.source_mode.currentText(),
            domains=_lines(self.domains.toPlainText()),
            preferred_regions=_lines(self.preferred_regions.toPlainText()),
            social_enabled=self.social_enabled.isChecked(),
            min_relevance_score=self.threshold.value(),
            min_confidence_score=self.confidence_threshold.value(),
            poll_interval_seconds=self.poll_interval.value() or None,
            cooldown_minutes=self.cooldown.value() or None,
            official_rss_urls=_lines(self.official_urls.toPlainText()),
            report_include_timeline=self.include_timeline.isChecked(),
            report_include_source_comparison=self.include_source_comparison.isChecked(),
            report_include_user_action=self.include_user_action.isChecked(),
        )

    def _mark_dirty(self, *_args) -> None:
        if self._loading:
            return
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._update_controls()

    def _confirm_navigation(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.warning(
            self,
            text("topic_unsaved_title", self.language),
            text("topic_unsaved_prompt", self.language),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self._save_current(silent=True)
        if answer == QMessageBox.Discard:
            self._set_dirty(False)
            return True
        return False

    def _select_list_index(self, index: int) -> None:
        self.topic_list.blockSignals(True)
        try:
            for row in range(self.topic_list.count()):
                item = self.topic_list.item(row)
                if item and item.data(Qt.UserRole) == index:
                    self.topic_list.setCurrentRow(row)
                    break
            else:
                self.topic_list.clearSelection()
        finally:
            self.topic_list.blockSignals(False)

    def _update_list_summary(self, visible_count: int | None = None) -> None:
        total = len(self.config.topics)
        active = sum(1 for topic in self.config.topics if topic.enabled)
        shown = self.topic_list.count() if visible_count is None else visible_count
        self.topic_list_summary.setText(
            text("topic_list_summary", self.language, shown=shown, active=active, total=total)
        )

    def _update_controls(self) -> None:
        has_saved_topic = 0 <= self.current_index < len(self.config.topics)
        self.delete_button.setEnabled(has_saved_topic)
        self.toggle_button.setEnabled(has_saved_topic)
        self.preview_sources_button.setEnabled(True)
        self.save_button.setEnabled(True)
        if has_saved_topic:
            topic = self.config.topics[self.current_index]
            key = "topic_unsaved_changes" if self._dirty else "topic_editing_existing"
            display_name = self.name.text().strip() if self._dirty else topic.name
            self.editor_status.setText(text(key, self.language, name=display_name or topic.name))
        else:
            key = "topic_unsaved_changes" if self._dirty else "topic_new_draft"
            self.editor_status.setText(text(key, self.language, name=self.name.text().strip() or text("topic_new_draft", self.language)))

    def _preview_source_selection(self) -> None:
        try:
            topic = self._topic_from_form()
            validate_topic(topic)
            lines = topic_source_preview_lines(topic, self.config, self.language)
        except ConfigError as exc:
            show_error(self, text("topic_invalid_title", self.language), str(exc))
            return
        self.source_preview.setPlainText("\n".join(lines))


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
