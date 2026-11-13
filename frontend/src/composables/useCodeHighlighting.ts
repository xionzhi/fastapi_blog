import { nextTick, onBeforeUnmount, onMounted, watch, type Ref } from 'vue'
import { highlightCode } from '../utils/highlight'

export function useCodeHighlighting(root: Ref<HTMLElement | undefined>, html: () => string): void {
  let observer: IntersectionObserver | undefined
  let sequence = 0
  async function enhance(): Promise<void> {
    const current = ++sequence
    observer?.disconnect()
    await nextTick()
    if (current !== sequence || !root.value) return
    const blocks = root.value.querySelectorAll<HTMLElement>('pre code[class*="language-"]')
    if (!('IntersectionObserver' in window)) {
      blocks.forEach((block) => {
        void highlightCode(block).catch(() => {})
      })
      return
    }
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          observer?.unobserve(entry.target)
          void highlightCode(entry.target as HTMLElement).catch(() => {})
        }
      },
      { rootMargin: '200px' },
    )
    blocks.forEach((block) => observer?.observe(block))
  }
  onMounted(enhance)
  watch(html, enhance)
  onBeforeUnmount(() => {
    sequence++
    observer?.disconnect()
  })
}
