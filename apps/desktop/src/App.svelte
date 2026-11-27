<script lang="ts">
  import { getCurrentWindow } from '@tauri-apps/api/window'
  import { onMount, tick } from 'svelte'
  import NotesSettings from './lib/NotesSettings.svelte'
  import Icon from './lib/Icon.svelte'
  import FieldFrame from './lib/FieldFrame.svelte'
  import DeleteDialog from './lib/DeleteDialog.svelte'
  import PanelDivider from './lib/PanelDivider.svelte'
  import MarkdownEditor from './lib/MarkdownEditor.svelte'
  import {
    checkUpdate, createFolder, createNote, deleteNote, downloadUpdate, installUpdate, listLibrary, readNote, saveNote, setNotesRoot,
    updatesEnabled, type NoteSummary,
  } from './lib/bridge'

  type Section = 'notes' | 'settings'

  let section: Section = $state('notes')
  let settingsBusy = $state(false)
  let settingsChanged = $state(false)
  let noteFolderWidth = $state(176)
  let noteListWidth = $state(200)
  let dark = $state(true)
  let query = $state('')
  let searchOpen = $state(false)
  let searchInput: HTMLInputElement | undefined = $state()
  let searchButton: HTMLButtonElement | undefined = $state()
  let folders: string[] = $state([])
  let selectedFolder = $state('')
  let expandedFolders = $state(new Set<string>())
  let notes: NoteSummary[] = $state([])
  let activePath = $state('')
  let markdown = $state('')
  let savedMarkdown = ''
  let editor: ReturnType<typeof MarkdownEditor> | undefined = $state()
  let openingNote = $state(false)
  let dirty = $state(false)
  let saving = $state(false)
  let pendingSave: Promise<boolean> | undefined
  let saveFailed = $state(false)
  let noteFontSize = $state(16)
  let loading = $state(true)
  let errorMessage = $state('')
  let creating = $state<'folder' | 'note' | null>(null)
  let noteTitle = $state('')
  let folderTitle = $state('')
  let createBusy = $state(false)
  let deletingNote = $state(false)
  let noteDeleteDialog = $state<ReturnType<typeof DeleteDialog>>()
  let noteToDelete: string | undefined
  let canUpdate = $state(false)
  let updateVersion = $state<string | null>(null)
  let checking = $state(false)
  let downloading = $state(false)
  let updateReady = $state(false)
  let updating = $state(false)
  let updateMessage = $state('')

  const desktop = '__TAURI_INTERNALS__' in window

  let folderNotes = $derived(selectedFolder ? notes.filter((note) => parentPath(note.path) === selectedFolder) : notes)
  let searchTerm = $derived(query.trim().toLocaleLowerCase('ru'))
  let filteredNotes = $derived(folderNotes.filter((note) =>
    `${note.title} ${note.excerpt}`.toLocaleLowerCase('ru').includes(searchTerm),
  ))
  let activeNote = $derived(notes.find((note) => note.path === activePath))
  let navigating = $derived(loading || openingNote || saving || createBusy || deletingNote)

  $effect(() => {
    if (!activePath || !dirty || navigating || updating || saveFailed || markdown === savedMarkdown) return
    const timer = setTimeout(() => { void persist() }, 650)
    return () => clearTimeout(timer)
  })

  let visibleFolders = $derived.by(() => {
    const children = new Map<string, string[]>()
    const ordered = [...folders].sort((a, b) => a.localeCompare(b, 'ru', { numeric: true }))
    for (const path of ordered) {
      const parent = parentPath(path)
      const siblings = children.get(parent)
      if (siblings) siblings.push(path)
      else children.set(parent, [path])
    }
    const rows: { path: string; depth: number; hasChildren: boolean }[] = []
    function append(parent: string, depth: number) {
      for (const path of children.get(parent) ?? []) {
        rows.push({ path, depth, hasChildren: children.has(path) })
        if (expandedFolders.has(path)) append(path, depth + 1)
      }
    }
    append('', 0)
    return rows
  })

  function parentPath(path: string) {
    return path.slice(0, Math.max(0, path.lastIndexOf('/')))
  }

  async function toggleSearch() {
    searchOpen = !searchOpen
    if (!searchOpen) query = ''
    await tick()
    if (searchOpen) searchInput?.focus()
    else searchButton?.focus()
  }

  function updateDraft(content: string) {
    if (content !== markdown) saveFailed = false
    markdown = content
    dirty = content !== savedMarkdown
  }

  function captureDraft() {
    updateDraft(editor?.readMarkdown() ?? markdown)
  }

  function changeNoteFontSize(increase: boolean) {
    noteFontSize = Math.min(32, Math.max(10, noteFontSize + (increase ? 2 : -2)))
  }

  function changeSection(next: Section) {
    if (settingsBusy) return
    if (section === 'notes' && next !== 'notes') captureDraft()
    section = next
  }

  async function requestExit() {
    try {
      await getCurrentWindow().close()
    } catch {
      changeSection('notes')
      errorMessage = 'Не удалось закрыть приложение.'
    }
  }

  async function updateNotesFolder(path: string) {
    if (navigating) throw new Error('Дождитесь окончания работы с заметкой.')
    if (!(await persist())) throw new Error('Сохраните открытую заметку перед сменой папки.')
    await setNotesRoot(path)
    activePath = ''
    savedMarkdown = ''
    updateDraft('')
    folders = []
    notes = []
    selectedFolder = ''
    expandedFolders = new Set()
    creating = null
    query = ''
    try {
      const library = await listLibrary()
      folders = library.folders
      notes = library.notes
      errorMessage = ''
    } catch {
      errorMessage = 'Папка сохранена, но прочитать заметки пока не удалось.'
    }
  }

  async function openNote(path: string) {
    if (openingNote || saving || path === activePath) return
    openingNote = true
    try {
      errorMessage = ''
      const content = await readNote(path)
      if (!(await persist())) return
      activePath = path
      savedMarkdown = content
      updateDraft(content)
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : String(error)
    } finally {
      openingNote = false
      loading = false
    }
  }

  async function persist() {
    if (deletingNote) return false
    if (pendingSave) return pendingSave
    if (!activePath) return true
    captureDraft()
    if (!dirty) return true
    const write = writeDraft(activePath, markdown)
    pendingSave = write
    try {
      return await write
    } finally {
      pendingSave = undefined
    }
  }

  async function persistLatest() {
    if (pendingSave) await pendingSave
    return persist()
  }

  async function writeDraft(path: string, content: string) {
    try {
      saving = true
      errorMessage = ''
      await saveNote(path, content)
      savedMarkdown = content
      saveFailed = false
      captureDraft()
      return !dirty
    } catch (error) {
      saveFailed = markdown === content
      errorMessage = error instanceof Error ? error.message : String(error)
      return false
    } finally {
      saving = false
    }
  }

  function askToDeleteNote(note: NoteSummary) {
    noteToDelete = note.path
    void noteDeleteDialog?.open(`Файл «${note.path}» будет удалён с диска без возможности восстановления в приложении.`)
  }

  async function deleteSelectedNote() {
    const path = noteToDelete
    if (!path) return
    if (loading || openingNote || createBusy || deletingNote || updating) {
      throw new Error('Дождитесь окончания текущей операции с заметками.')
    }
    deletingNote = true
    try {
      if (pendingSave) await pendingSave
      await deleteNote(path)
      if (activePath === path) {
        activePath = ''
        savedMarkdown = ''
        updateDraft('')
        errorMessage = ''
      }
      notes = notes.filter(note => note.path !== path)
    } finally {
      deletingNote = false
    }
  }

  function toggleFolder(path: string) {
    const next = new Set(expandedFolders)
    if (!next.delete(path)) next.add(path)
    expandedFolders = next
  }

  function showFolder(path: string) {
    if (path && !expandedFolders.has(path)) toggleFolder(path)
    if (path === selectedFolder) return
    selectedFolder = path
    query = ''
    creating = null
    activePath = ''
    savedMarkdown = ''
    updateDraft('')
  }

  async function selectFolder(path: string) {
    if (navigating || updating) return
    if (path === selectedFolder) {
      showFolder(path)
      return
    }
    openingNote = true
    try {
      if (await persist()) {
        errorMessage = ''
        showFolder(path)
      }
    } finally {
      openingNote = false
    }
  }

  async function addFolder(event: SubmitEvent) {
    event.preventDefault()
    const title = folderTitle.trim()
    if (!title || navigating || updating) return
    createBusy = true
    try {
      errorMessage = ''
      const parent = selectedFolder
      const path = await createFolder(title, parent)
      folders = [...folders, path]
      if (parent && !expandedFolders.has(parent)) toggleFolder(parent)
      creating = null
      folderTitle = ''
      if (await persist()) showFolder(path)
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : String(error)
    } finally {
      createBusy = false
    }
  }

  async function addNote(event: SubmitEvent) {
    event.preventDefault()
    const title = noteTitle.trim()
    if (!title || navigating || updating) return
    createBusy = true
    try {
      if (!(await persist())) return
      const note = await createNote(title, selectedFolder)
      notes = [note, ...notes]
      creating = null
      noteTitle = ''
      query = ''
      await openNote(note.path)
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : String(error)
    } finally {
      createBusy = false
    }
  }

  async function lookForUpdate(manual = false) {
    if (checking || downloading || updateReady || updating || !canUpdate) return
    checking = true
    if (manual) updateMessage = ''
    try {
      updateVersion = await checkUpdate()
      if (manual && !updateVersion) updateMessage = 'Установлена последняя версия'
    } catch {
      if (manual) updateMessage = 'Не удалось проверить обновления'
    } finally {
      checking = false
    }
  }

  async function downloadAvailableUpdate() {
    if (downloading || checking || updateReady || !updateVersion) return
    downloading = true
    updateMessage = 'Скачиваю обновление…'
    try {
      await downloadUpdate()
      updateReady = true
      updateMessage = 'Обновление скачано'
    } catch {
      updateMessage = 'Не удалось скачать обновление. Попробуйте ещё раз.'
    } finally {
      downloading = false
    }
  }

  async function applyUpdate() {
    if (updating || openingNote || saving || createBusy || deletingNote || !updateReady) return
    updating = true
    updateMessage = 'Сохраняю заметку и устанавливаю обновление…'
    try {
      if (!(await persist())) {
        updateMessage = 'Сохраните заметку перед обновлением'
        return
      }
      await installUpdate()
      updateReady = false
      updateVersion = null
      updateMessage = 'Обновление установлено'
    } catch {
      updateMessage = 'Не удалось установить обновление. Попробуйте ещё раз.'
    } finally {
      updating = false
    }
  }

  onMount(() => {
    let disposed = false
    let updateTimer: ReturnType<typeof setInterval> | undefined
    let closing = false
    const unlistenClose = desktop
      ? getCurrentWindow().onCloseRequested(async (event) => {
        if (closing || settingsBusy || openingNote || createBusy || deletingNote || updating) {
          event.preventDefault()
          return
        }
        closing = true
        try {
          if (!(await persistLatest())) {
            event.preventDefault()
            changeSection('notes')
          }
        } finally {
          closing = false
        }
      }).catch(() => undefined)
      : undefined
    void (async () => {
      try {
        const library = await listLibrary()
        if (disposed) return
        folders = library.folders
        notes = library.notes
        if (notes[0]) await openNote(notes[0].path)
        else loading = false
      } catch (error) {
        loading = false
        errorMessage = error instanceof Error ? error.message : String(error)
      }
    })()
    void updatesEnabled().then((enabled) => {
      if (disposed || !enabled) return
      canUpdate = true
      void lookForUpdate()
      updateTimer = setInterval(() => { void lookForUpdate() }, 4 * 60 * 60 * 1000)
    }).catch(() => {})
    const shortcut = (event: KeyboardEvent) => {
      if (!event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return
      if (event.key.toLowerCase() === 's' || event.code === 'KeyS') {
        event.preventDefault()
        if (section === 'settings') document.querySelector<HTMLFormElement>('#app-settings-form')?.requestSubmit()
        else if (!updating) void persistLatest()
        return
      }
      if (section !== 'notes' || !activeNote || updating) return
      const increase = ['+', '='].includes(event.key) || ['Equal', 'NumpadAdd'].includes(event.code)
      const decrease = event.key === '-' || ['Minus', 'NumpadSubtract'].includes(event.code)
      if (!increase && !decrease) return
      event.preventDefault()
      changeNoteFontSize(increase)
    }
    window.addEventListener('keydown', shortcut, true)
    return () => {
      disposed = true
      clearInterval(updateTimer)
      void unlistenClose?.then((unlisten) => unlisten?.())
      window.removeEventListener('keydown', shortcut, true)
    }
  })
</script>

<svelte:head><title>My Simple AI</title></svelte:head>

<div class:light={!dark} class="app-frame">
  <aside class="rail" aria-label="Основное меню" inert={updating}>
    <nav class="nav-stack">
      <button class:active={section === 'notes'} class="rail-button" title="Заметки"
        aria-current={section === 'notes' ? 'true' : undefined}
        onclick={() => changeSection('notes')}><Icon name="note" size={17} /></button>
      <button class="rail-button" title="Сменить тему" onclick={() => dark = !dark}><Icon name={dark ? 'sun' : 'moon'} size={17} /></button>
      <button class:active={section === 'settings'} class="rail-button" title="Настройки"
        aria-current={section === 'settings' ? 'true' : undefined}
        onclick={() => changeSection('settings')}><Icon name="settings" size={17} /></button>
      <button class="rail-button danger" title="Выйти" disabled={!desktop || settingsBusy || openingNote || createBusy || deletingNote}
        onclick={requestExit}><Icon name="exit" size={17} /></button>
    </nav>
  </aside>

  <main class="workspace">
    <header class="topbar">
      <div class="title-block">
        <h1>{section === 'settings' ? 'Настройки' : 'Заметки'}</h1>
        {#if section === 'settings' && canUpdate}<p aria-live="polite">{updateMessage}</p>{/if}
      </div>
      <div class="top-actions">
        {#if section === 'settings' && canUpdate}
          {#if updateReady}
            <button class="button primary" disabled={updating || settingsBusy || openingNote || saving || createBusy || deletingNote} onclick={applyUpdate}>
              {updating ? 'Устанавливаю…' : 'Перезапустить для обновления'}
            </button>
          {:else if updateVersion}
            <button class="button primary" disabled={downloading || checking} onclick={downloadAvailableUpdate}>
              {downloading ? 'Скачиваю…' : `Обновить до ${updateVersion}`}
            </button>
          {:else}
            <button class="button update-check" disabled={checking || updating} onclick={() => lookForUpdate(true)}>
              {checking ? 'Проверяю…' : 'Проверить обновления'}
            </button>
          {/if}
        {/if}
        {#if section === 'settings'}
          <button class="button primary" type="submit" form="app-settings-form" disabled={!settingsChanged || settingsBusy || updating}>
            <Icon name="save" size={16} />Сохранить
          </button>
        {:else if section === 'notes' && activeNote}
          <div class:dirty class="save-state"><i></i>{saving ? 'Сохранение…' : dirty ? 'Не сохранено' : 'Сохранено'}</div>
          <button class="button primary" disabled={!dirty || saving || updating || deletingNote} onclick={persist}><Icon name="save" size={18} />Сохранить</button>
        {/if}
      </div>
    </header>

    {#if section === 'settings'}
      <NotesSettings onSave={updateNotesFolder} disabled={updating} bind:busy={settingsBusy} bind:changed={settingsChanged} />
    {:else}
      <div class="notes-layout" style:--note-folder-width={`${noteFolderWidth}px`} style:--note-list-width={`${noteListWidth}px`} inert={updating}>
        <section class="folder-panel" aria-label="Папки">
          <div class="panel-heading">
            <strong>Папки</strong>
            <button class="accent-button" title="Новая папка" disabled={navigating} aria-expanded={creating === 'folder'} onclick={() => creating = creating === 'folder' ? null : 'folder'}><Icon name="folder-plus" size={18} /></button>
          </div>
          <div class="folder-list">
            <button class="folder-root" class:active={!selectedFolder} aria-current={!selectedFolder ? 'true' : undefined} disabled={navigating} onclick={() => selectFolder('')}>
              <Icon name="note" size={17} /><span>Все заметки</span>
            </button>
            {#if creating === 'folder'}
              <form class="new-note-form folder-form" onsubmit={addFolder}>
                <FieldFrame>
                  <input aria-label="Имя папки" placeholder="Имя папки" maxlength="80" bind:value={folderTitle} required />
                </FieldFrame>
                <button class="button primary" disabled={navigating || !folderTitle.trim()}>Создать</button>
              </form>
            {/if}
            {#each visibleFolders as { path, depth, hasChildren } (path)}
              {@const title = path.split('/').at(-1)}
              <div class="folder-row" class:active={selectedFolder === path} style:--depth={depth}>
                {#if hasChildren}
                  <button class="folder-toggle" aria-expanded={expandedFolders.has(path)} title={expandedFolders.has(path) ? `Свернуть ${title}` : `Развернуть ${title}`} onclick={() => toggleFolder(path)}>
                    <Icon name="chevron" size={13} />
                  </button>
                {:else}
                  <span class="folder-toggle-spacer"></span>
                {/if}
                <button class="folder-select" title={path} aria-current={selectedFolder === path ? 'true' : undefined} disabled={navigating} onclick={() => selectFolder(path)}>
                  <Icon name="folder" size={15} /><span>{title}</span>
                </button>
              </div>
            {/each}
          </div>
          <PanelDivider bind:width={noteFolderWidth} storageKey="my-simple-ai-note-folder-width" label="Ширина панели папок" minWidth={134} maxWidth={300} />
        </section>
        <section class="library-panel" aria-label="Заметки">
          <div class="panel-heading">
            <div><strong>Заметки</strong><span>{folderNotes.length}</span></div>
            <div>
              <button class="accent-button" title="Поиск заметок" aria-expanded={searchOpen} bind:this={searchButton} onclick={toggleSearch}><Icon name="search" size={15} /></button>
              <button class="accent-button" title="Новая заметка" disabled={navigating} aria-expanded={creating === 'note'} onclick={() => creating = creating === 'note' ? null : 'note'}><Icon name="plus" size={16} /></button>
            </div>
          </div>
          {#if searchOpen}
            <div class="search">
              <FieldFrame>
                <input bind:this={searchInput} bind:value={query} aria-label="Поиск заметок" placeholder="Поиск заметок" onkeydown={(event) => { if (event.key === 'Escape') void toggleSearch() }} />
              </FieldFrame>
            </div>
          {/if}
          <div class="note-list">
            {#if creating === 'note'}
              <form class="new-note-form" onsubmit={addNote}>
                <FieldFrame>
                  <input aria-label="Имя заметки" placeholder="Имя заметки" maxlength="80" bind:value={noteTitle} required />
                </FieldFrame>
                <button class="button primary" disabled={navigating || !noteTitle.trim()}>Создать</button>
              </form>
            {/if}
            {#each filteredNotes as note (note.path)}
              <div class="note-row list-item-with-action" class:active={note.path === activePath}>
                <button type="button" class="note-card" title={note.title} aria-current={note.path === activePath ? 'true' : undefined} disabled={navigating} onclick={() => openNote(note.path)}>
                  {note.title}
                </button>
                <button type="button" class="list-delete" title="Удалить заметку" aria-label={`Удалить заметку «${note.title}»`}
                  disabled={navigating} onclick={() => askToDeleteNote(note)}><Icon name="trash" size={14} /></button>
              </div>
            {:else}
              {#if !loading && creating !== 'note'}
                <p class="list-empty">{searchTerm ? 'Ничего не найдено' : selectedFolder ? 'В папке пока нет заметок' : 'Пока нет заметок'}</p>
              {/if}
            {/each}
          </div>
          <PanelDivider bind:width={noteListWidth} storageKey="my-simple-ai-note-list-width" label="Ширина списка заметок" minWidth={176} maxWidth={330} />
        </section>
        <DeleteDialog bind:this={noteDeleteDialog} heading="Удалить заметку?" onDelete={deleteSelectedNote} />
        <section class="document-panel" aria-label="Документ">
          {#if errorMessage}<div class="error-banner" role="alert">{errorMessage}</div>{/if}
          {#if loading}
            <div class="loading"><i></i><span>Открываю заметку</span></div>
          {:else if activeNote}
            <div class="document-title"><h2>{activeNote.title}</h2><p title={activeNote.path}>{activeNote.path}</p></div>
            {#key activePath}
              <MarkdownEditor bind:this={editor} value={markdown} fontSize={noteFontSize} onChange={updateDraft} onZoom={changeNoteFontSize} />
            {/key}
          {:else}
            <div class="empty"><Icon name="note" size={23} /><h2>Выберите или создайте заметку</h2></div>
          {/if}
        </section>
      </div>
    {/if}
  </main>
</div>
