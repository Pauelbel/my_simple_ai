<script lang="ts">
  import { onMount } from 'svelte'
  import { on } from 'svelte/events'
  import { languages } from '@codemirror/language-data'
  import { CrepeBuilder } from '@milkdown/crepe/builder'
  import { blockEdit } from '@milkdown/crepe/feature/block-edit'
  import { codeMirror } from '@milkdown/crepe/feature/code-mirror'
  import { cursor } from '@milkdown/crepe/feature/cursor'
  import { imageBlock } from '@milkdown/crepe/feature/image-block'
  import { linkTooltip } from '@milkdown/crepe/feature/link-tooltip'
  import { listItem } from '@milkdown/crepe/feature/list-item'
  import { placeholder } from '@milkdown/crepe/feature/placeholder'
  import { table } from '@milkdown/crepe/feature/table'
  import { toolbar } from '@milkdown/crepe/feature/toolbar'
  import { topBar } from '@milkdown/crepe/feature/top-bar'
  import './markdown-editor.css'
  import { codeHighlight } from './code-highlight'

  let {
    value,
    fontSize,
    onChange,
    onZoom,
  }: {
    value: string
    fontSize: number
    onChange: (markdown: string) => void
    onZoom: (increase: boolean) => void
  } = $props()

  let shell: HTMLDivElement
  let root: HTMLDivElement
  let editor: CrepeBuilder | undefined
  let initialMarkdown: string
  let initialSerialization: string
  let notice = $state('')
  let failed = $state(false)
  let noticeTimer: ReturnType<typeof setTimeout> | undefined

  export function readMarkdown(): string | undefined {
    if (!editor) return undefined
    const serialized = editor.getMarkdown()
    return serialized === initialSerialization ? initialMarkdown : serialized
  }

  function showNotice(message: string) {
    notice = message
    clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => { notice = '' }, 1800)
  }

  onMount(() => {
    const stopWheelListener = on(shell, 'wheel', (event) => {
      if (!event.ctrlKey || event.altKey || event.metaKey || event.deltaY === 0) return
      event.preventDefault()
      onZoom(event.deltaY < 0)
    }, { passive: false, capture: true })
    let disposed = false
    initialMarkdown = value
    const crepe = new CrepeBuilder({ root, defaultValue: initialMarkdown })
      .addFeature(cursor)
      .addFeature(listItem)
      .addFeature(linkTooltip, {
        inputPlaceholder: 'Адрес ссылки',
        onCopyLink: () => { if (!disposed) showNotice('Ссылка скопирована') },
      })
      .addFeature(imageBlock, {
        inlineUploadButton: 'Выбрать файл',
        inlineUploadPlaceholderText: 'или вставить ссылку',
        blockUploadButton: 'Выбрать файл',
        blockUploadPlaceholderText: 'или вставить ссылку',
        blockConfirmButton: 'Вставить',
        blockCaptionPlaceholderText: 'Подпись к изображению',
      })
      .addFeature(blockEdit)
      .addFeature(placeholder, { text: 'Начните писать…', mode: 'block' })
      .addFeature(toolbar)
      .addFeature(codeMirror, {
        languages,
        theme: codeHighlight,
        copyText: 'Копировать',
        onCopy: () => { if (!disposed) showNotice('Код скопирован') },
        searchPlaceholder: 'Поиск языка',
        noResultText: 'Язык не найден',
      })
      .addFeature(table)
      .addFeature(topBar, {
        headingOptions: [
          { label: 'Текст', level: null },
          ...([1, 2, 3, 4, 5, 6] as const).map((level) => ({
            label: `Заголовок ${level}`, level,
          })),
        ],
      })
    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown, previous) => {
        if (editor && markdown !== previous) {
          onChange(markdown === initialSerialization ? initialMarkdown : markdown)
        }
      })
    })
    const creation = crepe.create().then(() => {
      if (disposed) return
      initialSerialization = crepe.getMarkdown()
      editor = crepe
    }).catch(() => {
      if (!disposed) failed = true
    })
    return () => {
      stopWheelListener()
      disposed = true
      editor = undefined
      clearTimeout(noticeTimer)
      void creation.then(() => crepe.destroy())
    }
  })
</script>

<div class="editor-shell" bind:this={shell} style:--note-font-size={`${fontSize}px`}>
  <div class="editor-mount" bind:this={root}></div>
  {#if failed}<div class="editor-feedback" role="alert">Не удалось открыть редактор заметки.</div>{/if}
  <div class="editor-feedback" class:visible={notice} role="status">{notice}</div>
</div>
