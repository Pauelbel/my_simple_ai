from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QColor, QKeySequence, QPalette

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QKeySequenceEdit,
    QSpinBox,
    QVBoxLayout,
)

from desktop_assistant.dictation.speech_model import model_directory, validate_model

from .store import Settings


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        notes_root: Path,
        save_preferences: Callable[..., bool],
        dark: bool = True,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.save_preferences = save_preferences
        self.setWindowTitle("Настройки")
        self.setFixedWidth(560)
        self.setObjectName("settingsDialog")
        self._apply_theme(dark)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(9)

        title = QLabel("Настройки ассистента")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        subtitle = QLabel("Настройте распознавание, горячую клавишу и хранилище заметок")
        subtitle.setObjectName("hint")
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        def section(text: str) -> None:
            label = QLabel(text)
            label.setObjectName("sectionTitle")
            layout.addWidget(label)

        def hint(text: str) -> None:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName("hint")
            layout.addWidget(label)

        section("Модель распознавания")
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
        section("Потоки процессора")
        hint("Сколько потоков использовать для распознавания. Больше потоков может ускорить работу, но сильнее нагрузит компьютер.")
        threads = QSpinBox()
        threads.setRange(1, 32)
        threads.setValue(int(settings.values["speech_cpu_threads"]))
        threads.setToolTip("Больше потоков может ускорить распознавание, но увеличивает нагрузку на процессор")
        layout.addWidget(threads)
        layout.addSpacing(6)
        section("Горячая клавиша записи")
        hint("Работает глобально: первое нажатие запускает запись, повторное — останавливает.")
        hotkey = QKeySequenceEdit(QKeySequence(settings.values.get("record_hotkey", "Ctrl+Shift+Space")))
        hotkey.setClearButtonEnabled(True)
        layout.addWidget(hotkey)
        layout.addSpacing(6)
        section("Папка заметок")
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
        buttons = QDialogButtonBox()
        cancel = buttons.addButton("Отмена", QDialogButtonBox.ButtonRole.RejectRole)
        save = buttons.addButton("Сохранить", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("primaryButton")
        cancel.clicked.connect(self.reject)

        def save_settings() -> None:
            try:
                sequence = hotkey.keySequence().toString()
                if not self.save_preferences(threads.value(), folder.text(), model.text(), sequence):
                    return
                self.accept()
            except (OSError, ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "Настройки", str(error))

        save.clicked.connect(save_settings)
        layout.addWidget(buttons)
        self.setFixedHeight(self.sizeHint().height())

    def _apply_theme(self, dark: bool) -> None:
        colors = ({
            "background": "#181a1d", "surface": "#202327", "hover": "#282c32",
            "pressed": "#313740", "border": "#30343a", "text": "#e2e5e9",
            "muted": "#969eaa", "disabled": "#555d68", "accent": "#96b6f1",
            "selection": "#242c38",
        } if dark else {
            "background": "#ffffff", "surface": "#f1f3f6", "hover": "#e9edf2",
            "pressed": "#dce3ed", "border": "#e1e5ea", "text": "#252a32",
            "muted": "#667180", "disabled": "#b1b8c3", "accent": "#4269a8",
            "selection": "#edf2fa",
        })
        palette = QPalette()
        roles = {
            QPalette.ColorRole.Window: "background", QPalette.ColorRole.Base: "surface",
            QPalette.ColorRole.AlternateBase: "hover", QPalette.ColorRole.Button: "surface",
            QPalette.ColorRole.WindowText: "text", QPalette.ColorRole.Text: "text",
            QPalette.ColorRole.ButtonText: "text", QPalette.ColorRole.ToolTipBase: "surface",
            QPalette.ColorRole.ToolTipText: "text", QPalette.ColorRole.Highlight: "accent",
            QPalette.ColorRole.HighlightedText: "background", QPalette.ColorRole.PlaceholderText: "muted",
        }
        for role, name in roles.items():
            palette.setColor(role, QColor(colors[name]))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QDialog#settingsDialog {{ background: {colors['background']}; color: {colors['text']}; }}
            QLabel {{ color: {colors['text']}; background: transparent; }}
            QLabel#dialogTitle {{ font-size: 20px; font-weight: 600; }}
            QLabel#sectionTitle {{ font-size: 14px; font-weight: 600; margin-top: 3px; }}
            QLabel#hint {{ color: {colors['muted']}; }}
            QLineEdit, QKeySequenceEdit, QSpinBox {{
                color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; border-radius: 5px;
                padding: 7px 9px; min-height: 20px;
                selection-background-color: {colors['accent']};
                selection-color: {colors['background']};
            }}
            QLineEdit:focus, QKeySequenceEdit:focus, QSpinBox:focus {{ border-color: {colors['accent']}; }}
            QLineEdit:disabled {{ color: {colors['muted']}; }}
            QPushButton {{
                color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; border-radius: 5px;
                padding: 8px 16px; min-height: 18px;
            }}
            QPushButton:hover {{ background: {colors['hover']}; }}
            QPushButton:pressed {{ background: {colors['pressed']}; }}
            QPushButton#primaryButton {{
                color: {colors['background']}; background: {colors['accent']};
                border-color: {colors['accent']}; font-weight: 600;
            }}
            QPushButton#primaryButton:hover {{ opacity: 0.9; }}
            QMenu, QAbstractItemView {{
                color: {colors['text']}; background: {colors['surface']};
                border: 1px solid {colors['border']}; outline: none;
                selection-background-color: {colors['selection']};
                selection-color: {colors['text']};
            }}
            QMenu::item {{ color: {colors['text']}; padding: 7px 24px 7px 12px; border-radius: 4px; }}
            QMenu::item:selected {{ color: {colors['text']}; background: {colors['hover']}; }}
            QMenu::item:disabled {{ color: {colors['disabled']}; }}
            QMenu::separator {{ height: 1px; background: {colors['border']}; margin: 4px 8px; }}
            QToolTip {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; padding: 5px; }}
        """)
