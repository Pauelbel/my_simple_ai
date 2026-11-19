from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from desktop_assistant.core.windowing import set_always_on_top
from desktop_assistant.dictation.speech_model import model_directory, validate_model

from .store import Settings


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        notes_root: Path,
        save_preferences: Callable[[int, str, str | None], bool],
        always_on_top: bool,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.save_preferences = save_preferences
        set_always_on_top(self, always_on_top)
        self.setWindowTitle("Настройки")
        self.setFixedWidth(560)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        def hint(text: str) -> None:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("color: palette(mid);")
            layout.addWidget(label)

        layout.addWidget(QLabel("Модель распознавания"))
        hint("Русская речь распознаётся локально, без интернета. Выберите многоязычную модель Faster Whisper в формате CTranslate2.")
        model = QLineEdit(settings.values.get("speech_model_directory") or str(model_directory()))
        model.setReadOnly(True)
        model.setToolTip(model.text())
        model_button = QPushButton("Выбрать…")
        model_row = QHBoxLayout()
        model_row.addWidget(model)
        model_row.addWidget(model_button)
        layout.addLayout(model_row)
        status = QLabel()
        status.setWordWrap(True)
        layout.addWidget(status)

        def update_model_status() -> None:
            model.setToolTip(model.text())
            try:
                validate_model(Path(model.text()))
                status.setText("Модель готова к использованию")
            except (RuntimeError, OSError):
                status.setText("Модель отсутствует или неполна. Подготовьте её по инструкции в README.")

        update_model_status()

        def choose_model() -> None:
            selected = QFileDialog.getExistingDirectory(self, "Папка модели распознавания", model.text())
            if selected:
                model.setText(selected)
                update_model_status()

        model_button.clicked.connect(choose_model)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Потоки процессора"))
        hint("Сколько потоков использовать для распознавания. Больше потоков может ускорить работу, но сильнее нагрузит компьютер.")
        threads = QSpinBox()
        threads.setRange(1, 32)
        threads.setValue(int(settings.values["speech_cpu_threads"]))
        threads.setToolTip("Больше потоков может ускорить распознавание, но увеличивает нагрузку на процессор")
        layout.addWidget(threads)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Папка заметок"))
        hint("Здесь хранятся Markdown-файлы. При смене папки существующие заметки остаются на прежнем месте.")
        folder = QLineEdit(str(notes_root))
        folder.setReadOnly(True)
        folder.setToolTip(folder.text())
        choose = QPushButton("Выбрать…")
        folder_row = QHBoxLayout()
        folder_row.addWidget(folder)
        folder_row.addWidget(choose)
        layout.addLayout(folder_row)

        def choose_folder() -> None:
            selected = QFileDialog.getExistingDirectory(self, "Папка заметок", folder.text())
            if selected:
                folder.setText(selected)
                folder.setToolTip(selected)

        choose.clicked.connect(choose_folder)
        layout.addSpacing(8)
        save = QPushButton("Сохранить")

        def save_settings() -> None:
            try:
                if not self.save_preferences(threads.value(), folder.text(), model.text()):
                    return
                self.accept()
            except (OSError, ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "Настройки", str(error))

        save.clicked.connect(save_settings)
        layout.addWidget(save)
        self.setFixedHeight(self.sizeHint().height())
