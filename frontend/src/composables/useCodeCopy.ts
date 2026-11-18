import { onMounted, onScopeDispose, ref, watch, type Ref } from 'vue'
import { notify } from '../stores/notifications'

/** Add copy controls to rendered article HTML without editing the stored content. */
export function useCodeCopy(root: Ref<HTMLElement | undefined>, content: () => string) {
  const copied = ref(false)
  let copiedButton: HTMLButtonElement | undefined
  let feedbackTimer: ReturnType<typeof setTimeout> | undefined

  function resetFeedback(): void {
    clearTimeout(feedbackTimer)
    copiedButton?.removeAttribute('data-copied')
    copiedButton = undefined
    copied.value = false
  }

  async function copy(block: HTMLPreElement, button: HTMLButtonElement): Promise<void> {
    try {
      await navigator.clipboard.writeText(block.innerText)
      if (!button.isConnected) return
      resetFeedback()
      copiedButton = button
      button.dataset.copied = ''
      copied.value = true
      feedbackTimer = setTimeout(resetFeedback, 1800)
    } catch {
      if (button.isConnected) notify('Clipboard access is unavailable. Please copy manually.')
    }
  }

  function enhance(): void {
    for (const block of root.value?.querySelectorAll('pre') ?? []) {
      if (block.parentElement?.classList.contains('article-code')) continue

      const wrapper = document.createElement('div')
      wrapper.className = 'article-code'

      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'article-code-copy'
      button.title = 'Copy code'
      button.setAttribute('aria-label', 'Copy code')
      button.addEventListener('click', (event) => {
        event.preventDefault()
        void copy(block, button)
      })

      block.before(wrapper)
      wrapper.append(block, button)
    }
  }

  onMounted(enhance)
  watch(
    content,
    () => {
      resetFeedback()
      enhance()
    },
    { flush: 'post' },
  )
  onScopeDispose(resetFeedback)
  return copied
}
