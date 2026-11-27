<script lang="ts">
  import { onMount } from 'svelte'

  let { width = $bindable(), storageKey, label, minWidth = 148, maxWidth = 360 }: {
    width: number
    storageKey: string
    label: string
    minWidth?: number
    maxWidth?: number
  } = $props()

  let drag = $state<{ pointerId: number; startX: number; startWidth: number } | null>(null)

  onMount(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      if (stored !== null && Number.isFinite(Number(stored))) setWidth(Number(stored))
    } catch {
      // The panel uses its default width when storage is unavailable.
    }
  })

  function setWidth(value: number) {
    width = Math.round(Math.min(maxWidth, Math.max(minWidth, value)))
  }

  function saveWidth() {
    try {
      localStorage.setItem(storageKey, String(width))
    } catch {
      // The width still applies to the current window.
    }
  }

  function startResize(event: PointerEvent) {
    if (event.button !== 0 || drag) return
    event.preventDefault()
    const handle = event.currentTarget as HTMLElement
    handle.focus()
    drag = { pointerId: event.pointerId, startX: event.clientX, startWidth: width }
    try {
      handle.setPointerCapture(event.pointerId)
    } catch {
      // Window listeners still receive pointer moves within the application.
    }
  }

  function resize(event: PointerEvent) {
    if (drag?.pointerId !== event.pointerId) return
    if (event.buttons === 0) {
      finishResize()
      return
    }
    setWidth(drag.startWidth + event.clientX - drag.startX)
  }

  function finishResize(event?: PointerEvent) {
    if (!drag || (event && drag.pointerId !== event.pointerId)) return
    drag = null
    saveWidth()
  }

  function resizeWithKeyboard(event: KeyboardEvent) {
    if (event.key === 'Home') setWidth(minWidth)
    else if (event.key === 'End') setWidth(maxWidth)
    else if (event.key === 'ArrowLeft') setWidth(width - 12)
    else if (event.key === 'ArrowRight') setWidth(width + 12)
    else return
    event.preventDefault()
    saveWidth()
  }
</script>

<svelte:window onpointermove={resize} onpointerup={finishResize} onpointercancel={finishResize} onblur={() => finishResize()} />

<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions (Focusable window splitter.) -->
<div class="resize-handle" class:dragging={drag !== null} role="separator" tabindex="0"
  aria-label={label} aria-orientation="vertical" aria-valuemin={minWidth} aria-valuemax={maxWidth}
  aria-valuenow={width} title={label}
  onpointerdown={startResize} onlostpointercapture={finishResize} onkeydown={resizeWithKeyboard}></div>

<style>
  .resize-handle {
    position: absolute;
    inset-block: 0;
    inset-inline-end: -7px;
    width: 14px;
    cursor: ew-resize;
    touch-action: none;
    z-index: 2;
  }

  .resize-handle:hover::after, .resize-handle:focus-visible::after, .resize-handle.dragging::after {
    content: '';
    position: absolute;
    inset-block: 0;
    inset-inline-start: 6px;
    width: 2px;
    background: var(--accent);
  }
</style>
