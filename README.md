# My Simple AI

Настольное приложение на Tauri для локальных Markdown-заметок. Документы можно редактировать в оформленном виде с подсветкой кода, ссылками, таблицами и списками.

## Установка

[![Скачать для Windows x64](https://img.shields.io/badge/%D0%A1%D0%BA%D0%B0%D1%87%D0%B0%D1%82%D1%8C%20%D0%B4%D0%BB%D1%8F%20Windows%20x64-0969DA?style=for-the-badge)](https://github.com/Pauelbel/my_simple_ai/releases/latest/download/My-Simple-AI_windows-x86_64-setup.exe)
[![Скачать для Linux x86_64](https://img.shields.io/badge/%D0%A1%D0%BA%D0%B0%D1%87%D0%B0%D1%82%D1%8C%20%D0%B4%D0%BB%D1%8F%20Linux%20x64-BC4C00?style=for-the-badge)](https://github.com/Pauelbel/my_simple_ai/releases/latest/download/My-Simple-AI_linux-x86_64.AppImage)

Подписанные выпуски доступны в [Releases](https://github.com/Pauelbel/my_simple_ai/releases) и в [реестре GitHub Packages](https://github.com/Pauelbel/my_simple_ai/packages). Тестовые пакеты доступны в Artifacts успешной сборки [Tauri packages](https://github.com/Pauelbel/my_simple_ai/actions/workflows/tauri-check.yml).

- **Windows 11 x64.** Запустите `*-setup.exe` и откройте My Simple AI из меню «Пуск». Установщик работает для текущего пользователя и при необходимости скачивает WebView2.
- **Linux x86_64.** Сохраните `*.AppImage` в папку, доступную на запись, например `~/Applications`. Разрешите запуск в свойствах файла или командой `chmod +x имя-файла.AppImage`, затем откройте его. Если система сообщает, что FUSE 2 отсутствует, запустите файл в терминале с параметром `--appimage-extract-and-run`.

В подписанном выпуске приложение проверяет обновления при открытии и каждые четыре часа. Если есть новая версия, нажмите «Обновить». Приложение сохранит текущую заметку, проверит подпись пакета и перезапустится после установки. Тестовые сборки предназначены для ручной проверки.

## Заметки

Заметки лежат в `My Simple AI/notes` внутри системной папки «Документы». Чтобы перенести старую библиотеку, скопируйте содержимое её папки, включая подпапки, в новый каталог. Прежний путь можно уточнить по полю `notes_directory` в старом `settings.json`. Типичный путь на Linux — `~/.local/share/DesktopAssistant/notes`.

Текущий выпуск охватывает рабочее пространство и заметки. Диктовка в чате и история распознавания запланированы.

## Разработка и выпуск

- Linux: `bash dev-tauri.sh` из корня проекта.
- Windows: `.\dev-tauri.bat` из корня проекта.
- Браузерная проверка интерфейса: `npm ci` и `npm run dev` в `apps/desktop`.

Для сборки из исходников нужны Node.js 22, Rust и [системные зависимости Tauri](https://v2.tauri.app/start/prerequisites/). Порядок выпуска и настройка подписи описаны в [спецификации распространения](docs/specs/distribution.md). Остальные требования собраны в [спецификациях](docs/specs/README.md).
