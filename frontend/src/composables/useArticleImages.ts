import { onMounted, ref, watch, type Ref } from 'vue'

/** Enhance article HTML without changing stored content or linked-image navigation. */
export function useArticleImages(root: Ref<HTMLElement | undefined>, content: () => string) {
  const image = ref<{ src: string; alt: string } | null>(null)
  function enhance(): void {
    for (const element of root.value?.querySelectorAll('img') ?? []) {
      if (element.closest('a')) continue
      element.tabIndex = 0
      element.setAttribute('role', 'button')
      element.setAttribute('aria-haspopup', 'dialog')
      element.setAttribute('aria-label', element.alt ? `View image: ${element.alt}` : 'View image')
    }
  }
  function open(event: MouseEvent | KeyboardEvent): void {
    if (
      !(event.target instanceof HTMLImageElement) ||
      event.target.closest('a') ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey
    )
      return
    event.preventDefault()
    event.target.focus({ preventScroll: true })
    image.value = { src: event.target.src, alt: event.target.alt }
  }
  function keyboard(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') open(event)
  }
  onMounted(enhance)
  watch(
    content,
    () => {
      image.value = null
      enhance()
    },
    { flush: 'post' },
  )
  return { image, open, keyboard }
}
