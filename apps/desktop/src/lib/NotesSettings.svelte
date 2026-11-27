<script lang="ts">
  import { onMount } from 'svelte'
  import FieldFrame from './FieldFrame.svelte'
  import { getNotesRoot, pickNotesRoot } from './bridge'

  let { onSave, disabled, busy = $bindable(false), changed = $bindable(false) }: {
    onSave: (path: string) => Promise<void>
    disabled: boolean
    busy: boolean
    changed: boolean
  } = $props()

  let notesRoot = $state('')
  let chosenRoot = $state('')
  let status = $state('')

  onMount(async () => {
    changed = false
    try {
      notesRoot = await getNotesRoot()
    } catch (error) {
      status = String(error)
    }
  })

  function selectPath(path: string) {
    chosenRoot = path === notesRoot ? '' : path
    changed = Boolean(chosenRoot)
    status = ''
  }

  async function chooseFolder() {
    if (disabled || busy) return
    busy = true
    status = ''
    try {
      const path = await pickNotesRoot()
      if (path) selectPath(path)
    } catch (error) {
      status = String(error)
    } finally {
      busy = false
    }
  }

  async function save(event: SubmitEvent) {
    event.preventDefault()
    if (disabled || busy || !chosenRoot) return
    busy = true
    status = ''
    try {
      await onSave(chosenRoot)
      notesRoot = chosenRoot
      selectPath('')
      status = 'Папка сохранена.'
    } catch (error) {
      status = String(error)
    } finally {
      busy = false
    }
  }
</script>

<form id="app-settings-form" class="settings-content" onsubmit={save}>
  <section class="settings-card" aria-labelledby="notes-folder-title">
    <h2 id="notes-folder-title">Папка заметок</h2>
    <label>Место хранения
      <FieldFrame>
        <input value={chosenRoot || notesRoot} placeholder="Выберите папку для заметок" readonly />
      </FieldFrame>
    </label>
    <p>В этой папке будут открываться и создаваться заметки. Существующие файлы останутся в прежней папке.</p>
    <div class="settings-actions">
      <button type="button" class="button" disabled={busy || disabled} onclick={chooseFolder}>Выбрать папку</button>
      {#if chosenRoot}
        <button type="button" class="button" disabled={busy || disabled} onclick={() => selectPath('')}>Отменить выбор</button>
      {/if}
    </div>
    {#if status}<p role="status">{status}</p>{/if}
  </section>
</form>

<style>
  .settings-content { min-height: 0; overflow: auto; padding: 20px 24px; }
  .settings-card {
    width: min(100%, 680px); margin-inline: auto; display: grid; gap: 10px;
    border: 1px solid var(--border); border-radius: 8px; padding: 16px; background: var(--surface);
  }
  h2 { font-size: 17px; margin: 0 0 4px; }
  p { color: var(--muted); font-size: 13px; line-height: 1.45; margin: 0; }
  label { display: grid; gap: 5px; font-size: 13px; }
  .settings-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>
