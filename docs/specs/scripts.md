# Пользовательские скрипты

## Цель

Скрипты меняются без пересборки приложения и без прав администратора.

## Расположение

```text
Документы/My Simple AI/scripts/
├── example/
│   ├── manifest.json
│   └── main.py
└── ...
```

## Manifest v1

```json
{
  "schemaVersion": 1,
  "id": "example",
  "name": "Пример",
  "entry": "main.py",
  "timeoutSeconds": 30,
  "permissions": ["clipboard:write"]
}
```

## Исполнение

- Каждый запуск — отдельный дочерний процесс.
- Working directory — каталог конкретного скрипта.
- Аргументы передаются JSON через stdin, результат JSON через stdout.
- stderr попадает в лог выполнения.
- По умолчанию timeout 30 секунд, maximum 10 минут.
- Процесс и его descendants завершаются при cancel/timeout.
- UI никогда не блокируется ожиданием скрипта.

## Permissions

Начальный allowlist: `clipboard:read`, `clipboard:write`, `notes:read`, `notes:write`, `network:http`. Необъявленная возможность запрещается. Network выключен по умолчанию.

Важно: обычный Python не является полноценной security sandbox. Скрипты считаются локальным доверенным кодом пользователя. Загруженные из интернета сценарии требуют предупреждения и явного подтверждения перед первым запуском.

## Обновление

- Кнопка «Обновить» перечитывает manifests.
- File watcher обновляет список с debounce 300 ms.
- Изменение `main.py` не требует npm/cargo build.
- Ошибка одного manifest не мешает загрузке остальных.
