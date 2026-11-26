<script lang="ts">
  import { onMount } from 'svelte'
  import { Crepe, CrepeFeature } from '@milkdown/crepe'
  import '@milkdown/crepe/theme/common/style.css'
  import './markdown-editor.css'
  import { codeHighlight } from './code-highlight'

  let {
    value,
    onChange,
  }: {
    value: string
    onChange: (markdown: string) => void
  } = $props()

  let root: HTMLDivElement
  let editor: Crepe | undefined
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
    let disposed = false
    initialMarkdown = value
    const crepe = new Crepe({
      root,
      defaultValue: initialMarkdown,
      features: {
        [CrepeFeature.Latex]: false,
        [CrepeFeature.TopBar]: true,
      },
      featureConfigs: {
        [CrepeFeature.CodeMirror]: {
          theme: codeHighlight,
          copyText: 'Копировать',
          onCopy: () => { if (!disposed) showNotice('Код скопирован') },
          searchPlaceholder: 'Поиск языка',
          noResultText: 'Язык не найден',
        },
        [CrepeFeature.LinkTooltip]: {
          inputPlaceholder: 'Вставьте адрес ссылки',
          onCopyLink: () => { if (!disposed) showNotice('Ссылка скопирована') },
        },
        [CrepeFeature.TopBar]: {
          headingOptions: [
            { label: 'Текст', level: null },
            ...([1, 2, 3, 4, 5, 6] as const).map((level) => ({
              label: `Заголовок ${level}`, level,
            })),
          ],
        },
        [CrepeFeature.Placeholder]: {
          text: 'Начните писать…',
          mode: 'block',
        },
      },
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
      disposed = true
      editor = undefined
      clearTimeout(noticeTimer)
      void creation.then(() => crepe.destroy())
    }
  })
</script>

<div class="editor-shell">
  <div class="editor-mount" bind:this={root}></div>
  {#if failed}<div class="editor-feedback" role="alert">Не удалось открыть редактор заметки.</div>{/if}
  <div class="editor-feedback" class:visible={notice} role="status">{notice}</div>
</div>
