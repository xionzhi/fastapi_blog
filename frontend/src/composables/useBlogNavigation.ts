import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import { useScrollLock } from './useScrollLock'

/** Keep global navigation listeners, focus, and scroll locking in one lifecycle-owned place. */
export function useBlogNavigation(closeButton: Ref<HTMLButtonElement | undefined>) {
  const route = useRoute()
  const admin = computed(() => route.path.startsWith('/workspace'))
  const menu = ref(false)
  const searching = ref(false)
  let previousFocus: HTMLElement | null = null
  const overlayOpen = computed(() => menu.value || searching.value)
  useScrollLock(overlayOpen)

  watch(
    () => route.fullPath,
    () => {
      menu.value = false
      searching.value = false
    },
  )
  watch(overlayOpen, async (open) => {
    if (open) previousFocus = document.activeElement as HTMLElement | null
    await nextTick()
    if (menu.value) closeButton.value?.focus()
    else if (!open && previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
  })

  const openMenu = (): void => {
    searching.value = false
    menu.value = true
  }
  const openSearch = (): void => {
    menu.value = false
    searching.value = true
  }
  function keyboard(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      menu.value = false
      searching.value = false
    }
    if ((event.ctrlKey || event.metaKey) && event.key === 'k' && !admin.value) {
      event.preventDefault()
      menu.value = false
      searching.value = !searching.value
    }
  }
  function trap(event: KeyboardEvent): void {
    if (event.key !== 'Tab') return
    const items = [
      ...(document.querySelector('.menu-drawer')?.querySelectorAll<HTMLElement>('a,button') ?? []),
    ]
    if (event.shiftKey && document.activeElement === items[0]) {
      event.preventDefault()
      items.at(-1)?.focus()
    } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
      event.preventDefault()
      items[0]?.focus()
    }
  }
  onMounted(() => {
    window.addEventListener('keydown', keyboard)
    document.addEventListener('blog-menu', openMenu)
    document.addEventListener('blog-search', openSearch)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('keydown', keyboard)
    document.removeEventListener('blog-menu', openMenu)
    document.removeEventListener('blog-search', openSearch)
  })
  return { admin, menu, searching, trap }
}
