import { ref, watch } from 'vue'
import { getPosts } from '../api/posts'
import { errorMessage } from '../utils/format'
import type { PostSummary } from '../types'
import { useDebouncedTask } from './useDebouncedTask'

export function usePostSearch() {
  const query = ref('')
  const results = ref<PostSummary[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  const task = useDebouncedTask(250)
  watch(query, () => {
    task.cancel()
    error.value = ''
    if (!query.value.trim()) {
      results.value = []
      total.value = 0
      loading.value = false
      return
    }
    loading.value = true
    task.schedule(async (signal) => {
      try {
        const result = await getPosts({ q: query.value.trim(), limit: 30 }, signal)
        if (signal.aborted) return
        results.value = result.items
        total.value = result.total
      } catch (cause) {
        if (!signal.aborted) error.value = errorMessage(cause)
      } finally {
        if (!signal.aborted) loading.value = false
      }
    })
  })
  return { query, results, total, loading, error }
}
