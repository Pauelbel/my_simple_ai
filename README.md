# Desktop Assistant

Помощник для голосового ввода и Markdown-заметок.

## Установка на Linux

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/Pauelbel/my_simple_ai.git
   cd my_simple_ai
   ```

2. Создайте окружение и установите зависимости (нужен Python 3.13):

   ```bash
   python3.13 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Для голосового ввода скачайте модель (около 486 МБ):

   ```bash
   .venv/bin/python scripts/prepare_speech_model.py
   ```

4. Запустите приложение:

   ```bash
   ./run.sh
   ```

Разрешите доступ к микрофону. Нажмите на сферу, продиктуйте текст и нажмите ещё раз: результат появится в буфере обмена. Распознавание работает без интернета и API-ключа.

Папку для заметок можно выбрать в меню приложения → «Настройки» → «Папка заметок». Существующие заметки остаются в прежней папке; файлы из выбранной папки появятся в приложении.

## Архитектура

Проект разделён по функциональным блокам, а не по общим папкам со смешанными файлами:

```text
desktop_assistant/             Исходный код приложения
├── __main__.py                Запуск и подключение QML к контроллерам
├── controller.py              Координация окон и общих параметров приложения
├── core/                      Общая инфраструктура: пути и поведение окон
├── dictation/                 Голосовой ввод
│   ├── controller.py          Состояния записи и распознавания
│   ├── recorder.py            Запись звука
│   ├── transcription.py       Локальное распознавание речи
│   └── speech_model.py        Расположение и проверка модели
├── notes/                     Заметки
│   ├── controller.py          Жизненный цикл окна и смена библиотеки
│   ├── repository.py          Файлы, папки, поиск и операции с заметками
│   ├── window.py              Модель редактора и окно заметок
│   └── qml/                   Интерфейс только этого блока
├── history/                   История распознаваний: хранение, окно, контроллер
├── settings/                  Настройки: JSON-хранилище и отдельный диалог
├── ui/
│   ├── components/            Общие тема, кнопки, поля, меню и иконки
│   └── overlay/               Окно помощника и независимая анимация сферы
└── assets/                    Иконки и звуки

integrations/
├── desktop/                   Ярлык запуска для окружения рабочего стола
└── kwin/                      Необязательное расширение KDE/KWin для Wayland

data/speech-models/            Скачанные модели; не хранятся в Git
scripts/                       Вспомогательные команды установки и подготовки
tests/                         Автоматические тесты
```

Зависимости направлены от точки запуска к функциональным блокам. Блоки не обращаются к `AssistantController`: например, заметки работают через `NotesController` и `NotesRepository`, а запись — через `DictationController`. `AssistantController` только собирает блоки, открывает окна и применяет общее закрепление поверх окон.

### Работа с блоками по отдельности

Файловое хранилище заметок можно использовать без окна заметок и без голосового ввода:

```python
from desktop_assistant.notes.repository import NotesRepository

notes = NotesRepository("/path/to/notes")
path = notes.create_note("", "Идея")
notes.save(path, "# Идея\n\nТекст")
```

Настройки хранятся отдельно от диалога:

```python
from desktop_assistant.settings.store import Settings

settings = Settings()
settings.save({"speech_cpu_threads": 8})
```

Голосовой блок принимает зависимости через конструктор, поэтому рекордер и распознаватель можно заменить при тестировании или использовать контроллер отдельно от главного QML-окна:

```python
from desktop_assistant.dictation.controller import DictationController
from desktop_assistant.history.repository import RecognitionHistory
from desktop_assistant.settings.store import Settings

dictation = DictationController(app, Settings(), RecognitionHistory())
dictation.toggleRecording()
```

Анимация находится в `desktop_assistant/ui/overlay/OrbAnimation.qml` и зависит только от строкового свойства `status`: `idle`, `recording` или `processing`. Звук, меню, микрофон и распознавание в компонент анимации не входят.

## Проверка

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  .venv/bin/python -m unittest discover -s tests
```
