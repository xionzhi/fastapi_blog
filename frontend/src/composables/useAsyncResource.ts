import { onScopeDispose, ref, shallowRef, watch, type WatchSource } from 'vue'
import { errorMessage } from '../utils/format'

/** Keep the last result visible while replacing it; cancel superseded requests. */
export function useAsyncResource<T>(
  source: WatchSource<unknown>,
  fetchResource: (signal: AbortSignal) => Promise<T>,
) {
  const data = shallowRef<T>()
  const loading = ref(false)
  const error = ref('')
  let request: AbortController | undefined

  async function reload(): Promise<void> {
    request?.abort()
    const current = new AbortController()
    request = current
    loading.value = true
    error.value = ''
    try {
      const result = await fetchResource(current.signal)
      if (!current.signal.aborted) data.value = result
    } catch (cause) {
      if (!current.signal.aborted) error.value = errorMessage(cause)
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }

  watch(source, reload, { immediate: true })
  onScopeDispose(() => request?.abort())
  return { data, loading, error, reload }
}
