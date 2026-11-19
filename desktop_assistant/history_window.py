from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from .services.history import RecognitionHistory


class HistoryWindow(QDialog):
    def __init__(self, history: RecognitionHistory) -> None:
        super().__init__()
        self.history = history
        self.setWindowTitle("История распознавания")
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        buttons = QHBoxLayout()
        self.clear_button = QPushButton("Очистить историю")
        self.clear_button.clicked.connect(self.clear_history)
        buttons.addWidget(self.clear_button)
        buttons.addStretch()
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        items = self.history.list()
        text = "\n\n".join(f"{item['created_at']}\n{item['text']}" for item in items)
        self.text.setPlainText(text or "История пока пуста.")
        self.clear_button.setEnabled(bool(items))

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
