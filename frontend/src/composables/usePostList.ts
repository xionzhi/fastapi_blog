import { onScopeDispose, ref, watch } from 'vue'
import { useWorkspaceExitGuard } from './useWorkspaceExitGuard'
import { deletePost, getAdminPosts, getPostStatistics, type PostStatistics } from '../api/posts'
import type { Page, AdminPostSummary as Post } from '../types'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'
import { useDebouncedTask } from './useDebouncedTask'

export function usePostList() {
  const data = ref<Page<Post>>()
  const stats = ref<PostStatistics>({ total: 0, draft: 0, published: 0, tags: 0 })
  const q = ref('')
  const status = ref('')
  const page = ref(1)
  const loading = ref(false)
  const busy = ref(false)
  const error = ref('')
  const deleteTarget = ref<Post>()
  const deleteError = ref('')
  const searchTask = useDebouncedTask(250)
  let request: AbortController | undefined
  let disposed = false

  async function load(): Promise<void> {
    if (busy.value) return
    request?.abort()
    const current = new AbortController()
    request = current
    loading.value = true
    error.value = ''
    try {
      const [posts, counts] = await Promise.all([
        getAdminPosts(
          { page: page.value, q: q.value.trim(), status: status.value },
          current.signal,
        ),
        getPostStatistics(current.signal),
      ])
      if (current.signal.aborted) return
      data.value = posts
      stats.value = counts
      if (page.value > posts.pages) page.value = Math.max(1, posts.pages)
    } catch (cause) {
      if (!current.signal.aborted) error.value = errorMessage(cause)
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }
  async function resetPageAndLoad(): Promise<void> {
    if (page.value !== 1) page.value = 1
    else await load()
  }
  watch(q, () => searchTask.schedule(resetPageAndLoad))
  watch(status, () => {
    searchTask.cancel()
    void resetPageAndLoad()
  })
  watch(page, load)

  function askDelete(post: Post): void {
    if (busy.value || loading.value) return
    deleteTarget.value = post
    deleteError.value = ''
  }
  function cancelDelete(): void {
    if (!busy.value) {
      deleteTarget.value = undefined
      deleteError.value = ''
    }
  }
  async function remove(): Promise<void> {
    const post = deleteTarget.value
    if (!post || busy.value) return
    busy.value = true
    deleteError.value = ''
    searchTask.cancel()
    request?.abort()
    loading.value = false
    const criteria = JSON.stringify([q.value, status.value, page.value])
    let refresh = false
    let nextPage = page.value
    try {
      await deletePost(post.id)
      if (disposed) return
      if (data.value) {
        data.value.items = data.value.items.filter((item) => item.id !== post.id)
        data.value.total = Math.max(0, data.value.total - 1)
        data.value.pages = Math.max(1, Math.ceil(data.value.total / data.value.limit))
        if (!data.value.items.length) {
          nextPage = Math.min(page.value, data.value.pages)
          refresh = data.value.total > 0
        }
      }
      stats.value.total = Math.max(0, stats.value.total - 1)
      stats.value[post.status] = Math.max(0, stats.value[post.status] - 1)
      deleteTarget.value = undefined
      notify('Post deleted')
    } catch (cause) {
      if (!disposed) deleteError.value = errorMessage(cause)
    } finally {
      if (!disposed) busy.value = false
    }
    if (disposed) return
    if (nextPage !== page.value) page.value = nextPage
    else if (refresh || criteria !== JSON.stringify([q.value, status.value, page.value]))
      await load()
  }
  useWorkspaceExitGuard(() => {
    if (!busy.value) return true
    notify('Wait for the deletion to finish before leaving this page.')
    return false
  })
  onScopeDispose(() => {
    disposed = true
    request?.abort()
  })
  void load()
  return {
    data,
    stats,
    q,
    status,
    page,
    loading,
    busy,
    error,
    deleteTarget,
    deleteError,
    load,
    askDelete,
    cancelDelete,
    remove,
  }
}
