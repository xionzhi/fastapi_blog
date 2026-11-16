import { computed, nextTick, onScopeDispose, ref, watch } from 'vue'
import { useScrollLock } from './useScrollLock'

export function useImageLightbox(content: () => string) {
  const image = ref('')
  const dialog = ref<HTMLElement>()
  let previousFocus: HTMLElement | null = null
  let background: HTMLElement | null = null
  let originalInert = false
  useScrollLock(computed(() => Boolean(image.value)))

  function restore(): void {
    if (background) background.inert = originalInert
    background = null
  }
  watch(
    image,
    async (value, previous) => {
      if (value && !previous) {
        previousFocus =
          document.activeElement instanceof HTMLElement ? document.activeElement : null
        background = document.getElementById('app')
        originalInert = background?.inert ?? false
        if (background) background.inert = true
      } else if (!value) {
        restore()
      }
      await nextTick()
      if (image.value) dialog.value?.querySelector('button')?.focus({ preventScroll: true })
      else if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    },
    { flush: 'post' },
  )
  watch(content, () => {
    image.value = ''
  })
  onScopeDispose(restore)

  function open(event: MouseEvent): void {
    if (event.target instanceof HTMLImageElement) {
      event.preventDefault()
      image.value = event.target.src
    }
  }
  return { image, dialog, open }
}
