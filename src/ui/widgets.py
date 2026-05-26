from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLayout, QLineEdit, QMessageBox, QWidget

MESSAGE_BOX_STYLE = """
QMessageBox {
    background-color: #ffffff;
    color: #172033;
    min-width: 560px;
    min-height: 240px;
}
QMessageBox QLabel {
    color: #172033;
    background-color: transparent;
    font-size: 14px;
}
QMessageBox QPushButton {
    background-color: #075fb8;
    color: #ffffff;
    border: 0;
    border-radius: 6px;
    min-width: 80px;
    padding: 7px 14px;
    font-weight: 600;
}
QMessageBox QPushButton:hover {
    background-color: #064f96;
}
"""


def secret_line_edit(text: str = "") -> QLineEdit:
    field = QLineEdit(text)
    field.setEchoMode(QLineEdit.Password)
    field.setPlaceholderText("Stored in local .env, never in source code")
    return field


def show_error(parent: QWidget, title: str, message: str) -> None:
    _show_message(parent, title, message, QMessageBox.Critical)


def show_info(parent: QWidget, title: str, message: str) -> None:
    _show_message(parent, title, message, QMessageBox.Information)


def _show_message(parent: QWidget, title: str, message: str, icon: QMessageBox.Icon) -> None:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(message)
    box.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet(MESSAGE_BOX_STYLE)
    box.setMinimumSize(600, 280)
    if box.layout():
        box.layout().setSizeConstraint(QLayout.SetNoConstraint)
    for label in box.findChildren(QLabel):
        label.setWordWrap(True)
        label.setMinimumWidth(500)
    box.resize(640, 320)
    box.exec()
