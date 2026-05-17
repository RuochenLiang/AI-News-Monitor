from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.i18n import text


class LogsPage(QWidget):
    def __init__(self, runtime_dir: Path):
        super().__init__()
        self.runtime_dir = runtime_dir
        self.language = "en"
        self.lines: list[str] = []
        self.filter = QComboBox()
        self.filter.addItems([text("all", self.language), "Info", "Warning", "Error", "Alerts"])
        self.open_button = QPushButton(text("open_logs", self.language))
        self.text = QTextEdit()
        self.text.setReadOnly(True)

        layout = QVBoxLayout(self)
        self.title_label = QLabel(text("logs_title", self.language))
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)
        controls = QHBoxLayout()
        self.filter_label = QLabel(text("filter", self.language))
        controls.addWidget(self.filter_label)
        controls.addWidget(self.filter)
        controls.addStretch(1)
        controls.addWidget(self.open_button)
        layout.addLayout(controls)
        layout.addWidget(self.text, 1)

        self.filter.currentTextChanged.connect(self._render)
        self.open_button.clicked.connect(self.open_logs_folder)
        self.load_existing()

    def apply_language(self, language: str) -> None:
        current = self.filter.currentText()
        self.language = language
        self.title_label.setText(text("logs_title", language))
        self.filter_label.setText(text("filter", language))
        self.open_button.setText(text("open_logs", language))
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItems([text("all", language), "Info", "Warning", "Error", "Alerts"])
        self.filter.setCurrentText(text("all", language) if current in {text("all", "zh-CN"), "All"} else current)
        self.filter.blockSignals(False)
        self._render()

    def append_log(self, message: str) -> None:
        lower = message.lower()
        prefix = "Error" if "error" in lower or "failed" in lower else "Info"
        self.lines.insert(0, f"{prefix}: {message}")
        self.lines = self.lines[:500]
        self._render()

    def load_existing(self) -> None:
        logs_dir = self.runtime_dir / "logs"
        collected: list[str] = []
        for label, filename in (("Info", "app.log"), ("Error", "error.log"), ("Alerts", "alerts.log")):
            path = logs_dir / filename
            if path.exists():
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-150:]:
                    collected.append(f"{label}: {line}")
        self.lines = list(reversed(collected[-500:]))
        self._render()

    def open_logs_folder(self) -> None:
        logs_dir = self.runtime_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))

    def _render(self) -> None:
        selected = self.filter.currentText()
        if selected in {text("all", "zh-CN"), "All"}:
            lines = self.lines
        else:
            needle = selected.lower()
            lines = [line for line in self.lines if needle in line.lower()]
        self.text.setPlainText("\n".join(lines))
