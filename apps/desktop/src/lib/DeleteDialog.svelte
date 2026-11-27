<script lang="ts">
  import { tick } from 'svelte'

  let { heading, onDelete }: {
    heading: string
    onDelete: () => void | Promise<void>
  } = $props()

  const id = $props.id()
  let dialog: HTMLDialogElement
  let cancelButton: HTMLButtonElement
  let description = $state('')
  let busy = $state(false)
  let errorMessage = $state('')

  export async function open(message: string) {
    description = message
    errorMessage = ''
    await tick()
    dialog.showModal()
    cancelButton.focus()
  }

  async function confirm(event: SubmitEvent) {
    event.preventDefault()
    if (busy) return
    busy = true
    try {
      await onDelete()
      dialog.close()
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : String(error)
      await tick()
      dialog.querySelector<HTMLElement>('[role="alert"]')?.focus()
    } finally {
      busy = false
    }
  }
</script>

<dialog bind:this={dialog} aria-labelledby={id} aria-describedby={`${id}-description`}
  oncancel={(event) => { if (busy) event.preventDefault() }}>
  <h2 id={id}>{heading}</h2>
  <p id={`${id}-description`}>{description}</p>
  {#if errorMessage}<p class="error" role="alert" tabindex="-1">{errorMessage}</p>{/if}
  <form onsubmit={confirm}>
    <button type="button" class="button" disabled={busy} bind:this={cancelButton} onclick={() => dialog.close()}>Отмена</button>
    <button type="submit" class="button delete" disabled={busy}>{busy ? 'Удаляю…' : 'Удалить'}</button>
  </form>
</dialog>

<style>
  dialog {
    width: min(360px, calc(100% - 32px));
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--text);
  }
  dialog::backdrop { background: rgb(0 0 0 / 45%); }
  h2 { margin: 0; font-size: 15px; }
  p { margin: 8px 0 12px; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
  .error, .delete { color: var(--danger); }
  form { display: flex; justify-content: flex-end; gap: 6px; }
</style>
