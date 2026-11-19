# Desktop Assistant

Настольный помощник с голосовым вводом и заметками в формате Markdown. Приложение написано на Python с использованием PySide6 и QML.

## Возможности

- Локальное распознавание русской речи и копирование текста в буфер обмена.
- История распознавания.
- Заметки с папками, поиском и просмотром Markdown.
- Светлая и тёмная темы, настройка окна поверх других окон.

## Установка и запуск

Рекомендуется Python 3.13.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/prepare_speech_model.py
python -m desktop_assistant
```

На Windows для создания и активации окружения используйте `py -3.13 -m venv .venv` и `.venv\Scripts\activate`. На Linux приложение также можно запустить командой `./run.sh`.

Скрипт подготовки скачивает модель распознавания размером около 486 МБ. После этого распознавание работает локально, без интернета и API-ключа.

Чтобы начать запись, нажмите на сферу или выберите «Голосовой ввод» в меню. Повторное нажатие завершит запись и запустит распознавание.

Заметки и настройки хранятся в папке данных приложения: `~/.local/share/DesktopAssistant` на Linux и `AppData/Local/DesktopAssistant` на Windows.

## Тесты

```bash
pip install -e '.[test]'
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python -m pytest
```

## Сборка

```bash
pip install -e '.[build]'
python scripts/prepare_speech_model.py
pyinstaller desktop-assistant.spec --noconfirm
```

Готовое приложение находится в `dist/DesktopAssistant`. Для переноса на другой компьютер скопируйте всю папку. Сборку для каждой операционной системы нужно создавать отдельно.
