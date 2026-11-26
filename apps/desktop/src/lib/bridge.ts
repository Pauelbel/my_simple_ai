import { invoke } from '@tauri-apps/api/core'

export interface NoteSummary {
  path: string
  title: string
  excerpt: string
  updated: string
}

interface Library {
  folders: string[]
  notes: NoteSummary[]
}

const demoFolders = ['Идеи', 'Идеи/Проекты', 'Архив']

const demoNotes: Record<string, string> = {
  'Добро пожаловать.md': [
    '# Добро пожаловать',
    '',
    'Заметки можно редактировать прямо здесь. Смотрите [справку по Markdown](https://commonmark.org/help/) или попробуйте встроенный код `notes.md`.',
    '',
    '## Блоки кода',
    '',
    '```python',
    'from pathlib import Path',
    '',
    '# Читаем заметку из локального файла',
    'for note in Path("notes").glob("*.md"):',
    '    print(note.name)',
    '```',
    '',
    '> Чтобы изменить подсветку, выберите язык в заголовке блока.',
    '',
    '## Быстрые клавиши',
    '',
    '| Действие | Клавиши |',
    '| --- | --- |',
    '| Сохранить | `Ctrl+S` |',
    '| Отменить | `Ctrl+Z` |',
    '',
    '- [x] Открыть заметку',
    '- [ ] Попробовать форматирование',
  ].join('\n'),
  'Идеи/Интерфейс.md': '# Интерфейс\n\n- Плавные панели\n- Насыщенные действия\n- Спокойная типографика',
}

function isTauri(): boolean {
  return '__TAURI_INTERNALS__' in window
}

export async function listLibrary(): Promise<Library> {
  if (isTauri()) return invoke<Library>('list_library')
  const notes = Object.entries(demoNotes).map(([path, content]) => ({
    path,
    title: path.split('/').at(-1)!.replace(/\.md$/i, ''),
    excerpt: content.replace(/[#*`>-]/g, '').replace(/\s+/g, ' ').trim().slice(0, 90),
    updated: 'сейчас',
  }))
  return { folders: [...demoFolders], notes }
}

export async function readNote(path: string): Promise<string> {
  if (isTauri()) return invoke<string>('read_note', { path })
  return demoNotes[path] ?? ''
}

export async function saveNote(path: string, content: string): Promise<void> {
  if (isTauri()) return invoke('save_note', { path, content })
  demoNotes[path] = content
}

export async function createFolder(title: string, folder: string): Promise<string> {
  if (isTauri()) return invoke<string>('create_folder', { title, folder })
  if (/[\\/:*?"<>|]/.test(title) || title.endsWith('.')) throw new Error('Введите допустимое имя папки')
  const path = folder ? `${folder}/${title}` : title
  if (demoFolders.includes(path) || Object.hasOwn(demoNotes, path)) {
    throw new Error('Папка с таким именем уже существует')
  }
  demoFolders.push(path)
  return path
}

export async function createNote(title: string, folder: string): Promise<NoteSummary> {
  if (isTauri()) return invoke<NoteSummary>('create_note', { title, folder })
  if (/[\\/:*?"<>|]/.test(title) || title.endsWith('.')) throw new Error('Введите допустимое имя заметки')
  const path = folder ? `${folder}/${title}.md` : `${title}.md`
  if (Object.hasOwn(demoNotes, path)) throw new Error('Заметка с таким именем уже существует')
  demoNotes[path] = `# ${title}\n`
  return { path, title, excerpt: '', updated: '' }
}

export async function updatesEnabled(): Promise<boolean> {
  return isTauri() && invoke<boolean>('updates_enabled')
}

export function checkUpdate(): Promise<string | null> {
  return invoke<string | null>('check_update')
}

export function downloadUpdate(): Promise<void> {
  return invoke('download_update')
}

export function installUpdate(): Promise<void> {
  return invoke('install_update')
}
