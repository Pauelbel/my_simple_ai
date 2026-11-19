from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from .repository import RecognitionHistory


class HistoryWindow(QDialog):
    def __init__(self, history: RecognitionHistory, dark: bool = True) -> None:
        super().__init__()
        self.history = history
        self.setWindowTitle("История распознавания")
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(560, 420)
        self.resize(680, 560)
        self.setObjectName("historyDialog")
        self.apply_theme(dark)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        title = QLabel("История распознавания")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        header = QHBoxLayout()
        subtitle = QLabel("Последние распознанные фразы сохраняются локально")
        subtitle.setObjectName("hint")
        header.addWidget(subtitle)
        header.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("counter")
        header.addWidget(self.count_label)
        layout.addLayout(header)
        layout.addSpacing(5)
        self.text = QPlainTextEdit()
        self.text.setObjectName("historyText")
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        buttons = QDialogButtonBox()
        self.clear_button = buttons.addButton("Очистить историю", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.clicked.connect(self.clear_history)
        close_button = buttons.addButton("Закрыть", QDialogButtonBox.ButtonRole.RejectRole)
        close_button.clicked.connect(self.close)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self) -> None:
        items = self.history.list()
        def format_date(value: str) -> str:
            try:
                return datetime.fromisoformat(value).strftime("%d.%m.%Y · %H:%M")
            except (TypeError, ValueError):
                return value

        text = "\n\n".join(f"{format_date(item['created_at'])}\n{item['text']}" for item in items)
        self.text.setPlainText(text or "История пока пуста.")
        self.clear_button.setEnabled(bool(items))
        count = len(items)
        self.count_label.setText(f"{count} " + ("запись" if count == 1 else "записи" if 2 <= count <= 4 else "записей"))

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "Очистка истории",
            "Удалить все записи из истории распознавания?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.history.clear()
        except OSError as error:
            QMessageBox.warning(self, "История распознавания", str(error))
            return
        self.refresh()

    def apply_theme(self, dark: bool) -> None:
        colors = ({
            "background": "#181a1d", "surface": "#202327", "hover": "#282c32",
            "pressed": "#313740", "border": "#30343a", "text": "#e2e5e9",
            "muted": "#969eaa", "disabled": "#555d68", "accent": "#96b6f1",
            "danger": "#e7a4a4", "selection": "#242c38",
        } if dark else {
            "background": "#ffffff", "surface": "#f1f3f6", "hover": "#e9edf2",
            "pressed": "#dce3ed", "border": "#e1e5ea", "text": "#252a32",
            "muted": "#667180", "disabled": "#b1b8c3", "accent": "#4269a8",
            "danger": "#ac4444", "selection": "#edf2fa",
        })
        palette = QPalette()
        for role, name in {
            QPalette.ColorRole.Window: "background", QPalette.ColorRole.Base: "surface",
            QPalette.ColorRole.AlternateBase: "hover", QPalette.ColorRole.Button: "surface",
            QPalette.ColorRole.WindowText: "text", QPalette.ColorRole.Text: "text",
            QPalette.ColorRole.ButtonText: "text", QPalette.ColorRole.ToolTipBase: "surface",
            QPalette.ColorRole.ToolTipText: "text", QPalette.ColorRole.Highlight: "accent",
            QPalette.ColorRole.HighlightedText: "background", QPalette.ColorRole.PlaceholderText: "muted",
        }.items():
            palette.setColor(role, QColor(colors[name]))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QDialog#historyDialog {{ background: {colors['background']}; color: {colors['text']}; }}
            QLabel {{ color: {colors['text']}; background: transparent; }}
            QLabel#dialogTitle {{ font-size: 20px; font-weight: 600; }}
            QLabel#hint {{ color: {colors['muted']}; }}
            QLabel#counter {{ color: {colors['accent']}; background: {colors['selection']};
                border-radius: 10px; padding: 3px 9px; }}
            QPlainTextEdit {{ color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; border-radius: 6px; padding: 14px;
                selection-background-color: {colors['accent']}; selection-color: {colors['background']};
                font-size: 14px; }}
            QPushButton {{ color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; border-radius: 5px;
                padding: 8px 16px; min-height: 18px; }}
            QPushButton:hover {{ background: {colors['hover']}; }}
            QPushButton:pressed {{ background: {colors['pressed']}; }}
            QPushButton:disabled {{ color: {colors['disabled']}; }}
            QPushButton#dangerButton {{ color: {colors['danger']}; }}
            QMenu {{ color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; padding: 4px; }}
            QMenu::item {{ color: {colors['text']}; padding: 7px 24px 7px 12px; border-radius: 4px; }}
            QMenu::item:selected {{ color: {colors['text']}; background: {colors['hover']}; }}
            QMenu::item:disabled {{ color: {colors['disabled']}; }}
            QMenu::separator {{ height: 1px; background: {colors['border']}; margin: 4px 8px; }}
            QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {colors['muted']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{ color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; padding: 5px; }}
        """)
