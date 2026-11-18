import { computed, onScopeDispose, ref } from 'vue'
import { getPosts } from '../api/posts'
import { errorMessage } from '../utils/format'
import type { PostSummary as Post } from '../types'

export function useArchive() {
  const posts = ref<Post[]>([])
  const total = ref<number>()
  const page = ref(0)
  const pages = ref(1)
  const loading = ref(false)
  const error = ref('')
  let request: AbortController | undefined
  const groups = computed(() => {
    const values: { year: string; posts: Post[] }[] = []
    for (const post of posts.value) {
      const year = post.published_at?.slice(0, 4) || ''
      let group = values.find((item) => item.year === year)
      if (!group) {
        group = { year, posts: [] }
        values.push(group)
      }
      group.posts.push(post)
    }
    return values
  })
  async function load(): Promise<void> {
    if (loading.value) return
    const current = new AbortController()
    request = current
    loading.value = true
    error.value = ''
    try {
      const data = await getPosts({ limit: 25, page: page.value + 1 }, current.signal)
      if (current.signal.aborted) return
      posts.value = [
        ...new Map([...posts.value, ...data.items].map((post) => [post.id, post])).values(),
      ]
      total.value = data.total
      page.value = data.page
      pages.value = data.pages
    } catch (cause) {
      if (!current.signal.aborted) error.value = errorMessage(cause)
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }
  onScopeDispose(() => request?.abort())
  void load()
  return { posts, total, page, pages, loading, error, groups, load }
}
