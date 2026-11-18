import { onBeforeUnmount, onMounted, watch, type WatchStopHandle } from 'vue'
import { useRoute } from 'vue-router'
import { recordPageView } from '../api/analytics'
import { session } from '../stores/session'

const STORAGE_KEY = 'blog-daily-visitor'
const PRIVATE_PATH = /^\/(?:(workspace|admin|api|assets|legacy|content)(\/|$)|preview\/[^/])/

function visitorId(): string | undefined {
  const privacy = navigator as Navigator & { globalPrivacyControl?: boolean }
  if (privacy.globalPrivacyControl || navigator.doNotTrack === '1') return
  try {
    const day = new Date().toISOString().slice(0, 10)
    const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (stored && typeof stored === 'object' && 'day' in stored && 'id' in stored) {
      if (stored.day === day && typeof stored.id === 'string') return stored.id
    }
    const id = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ day, id }))
    return id
  } catch {
    // Storage restrictions and privacy settings must not affect reading the blog.
    return
  }
}

export function usePageViews(): void {
  const route = useRoute()
  let stop: WatchStopHandle | undefined
  let timer: ReturnType<typeof setTimeout> | undefined
  let pending: string | undefined

  function flush(): void {
    if (document.visibilityState !== 'visible' || !pending) return
    const path = pending
    pending = undefined
    if (session.username || PRIVATE_PATH.test(path)) return
    const id = visitorId()
    if (id) void recordPageView(path, id).catch(() => {})
  }
  function queue(path: string): void {
    clearTimeout(timer)
    pending = path
    timer = setTimeout(flush, 400)
  }
  onMounted(() => {
    stop = watch(() => route.path, queue, { immediate: true })
    document.addEventListener('visibilitychange', flush)
  })
  onBeforeUnmount(() => {
    clearTimeout(timer)
    stop?.()
    document.removeEventListener('visibilitychange', flush)
  })
}
