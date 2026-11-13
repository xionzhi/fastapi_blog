<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Search, X, ArrowUpRight } from 'lucide-vue-next'
import { getPosts } from '../api/posts'
import { useDebouncedTask } from '../composables/useDebouncedTask'
import { errorMessage } from '../utils/format'
import type { PostSummary as Post } from '../types'
defineEmits<{ close: [] }>()
const query = ref('')
const results = ref<Post[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const input = ref<HTMLInputElement>()
const task = useDebouncedTask(250)
const previousFocus = document.activeElement as HTMLElement | null
onMounted(() => input.value?.focus())
onUnmounted(() => {
  task.cancel()
  previousFocus?.focus()
})
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
      const result = await getPosts({ q: query.value, limit: 30 }, signal)
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

function trap(e: KeyboardEvent) {
  if (e.key !== 'Tab') return
  const items = [
    ...document.querySelectorAll<HTMLElement>(
      '.search-dialog input,.search-dialog button,.search-dialog a',
    ),
  ]
  if (e.shiftKey && document.activeElement === items[0]) {
    e.preventDefault()
    items.at(-1)?.focus()
  } else if (!e.shiftKey && document.activeElement === items.at(-1)) {
    e.preventDefault()
    items[0]?.focus()
  }
}
</script>
<template>
  <div
    class="search-backdrop"
    @click.self="$emit('close')"
  >
    <section
      class="search-dialog"
      role="dialog"
      aria-modal="true"
      aria-label="Search posts"
      @keydown="trap"
    >
      <div class="search-field">
        <Search :size="22" />
        <input
          ref="input"
          v-model="query"
          placeholder="Search posts, topics, and keywords…"
          aria-label="Search keywords"
        />
        <button
          class="icon-button"
          aria-label="Close search"
          @click="$emit('close')"
        >
          <X :size="20" />
        </button>
      </div>
      <div
        class="search-results"
        aria-live="polite"
      >
        <p
          v-if="loading"
          class="muted"
        >
          Searching…
        </p>
        <p
          v-else-if="error"
          class="form-error"
        >
          {{ error }}
        </p>
        <p
          v-else-if="!query.trim()"
          class="muted"
        >
          Find a familiar thought, or discover something new.
        </p>
        <template v-else>
          <p class="search-count">
            {{ total }} posts
            <span v-if="total > 30">; showing the first 30. Refine your search to see more.</span>
          </p>
          <RouterLink
            v-for="post in results"
            :key="post.id"
            :to="`/${post.slug}/`"
          >
            <h3>
              {{ post.title }}
              <ArrowUpRight :size="18" />
            </h3>
            <p>{{ post.excerpt.slice(0, 100) }}</p>
          </RouterLink>
          <p
            v-if="!results.length"
            class="muted"
          >
            No matching posts. Try another search.
          </p>
        </template>
      </div>
      <div class="search-hint">
        <kbd>esc</kbd>
        Close
        <span>Full-text search</span>
      </div>
    </section>
  </div>
</template>
