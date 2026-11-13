<script setup lang="ts">
import { getPosts } from '../api/posts'

import { computed, ref } from 'vue'
import BlogNav from '../components/BlogNav.vue'
import { date, errorMessage } from '../utils/format'
import { site } from '../stores/site'
import type { PostSummary as Post } from '../types'
const posts = ref<Post[]>([])
const page = ref(0)
const pages = ref(1)
const loading = ref(false)
const error = ref('')
const groups = computed(() => {
  const values: { year: string; posts: Post[] }[] = []
  for (const post of posts.value) {
    const year = post.published_at?.slice(0, 4) || ''
    let group = values.find((g) => g.year === year)
    if (!group) {
      group = { year, posts: [] }
      values.push(group)
    }
    group.posts.push(post)
  }
  return values
})
async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getPosts({ limit: 25, page: page.value + 1 })
    posts.value.push(...data.items)
    page.value = data.page
    pages.value = data.pages
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
load()
document.title = `Archive · ${site.value.title}`
</script>
<template>
  <BlogNav />
  <main
    id="main-content"
    class="index-page archive-page"
  >
    <p class="eyebrow">THE ARCHIVE</p>
    <h1>The archive</h1>
    <p class="index-description">
      {{ site.stats?.posts || posts.length }} posts. Thoughts, notes, and discoveries.
    </p>
    <section
      v-for="group in groups"
      :key="group.year"
      class="archive-year"
    >
      <h2>{{ group.year }}</h2>
      <RouterLink
        v-for="post in group.posts"
        :key="post.id"
        :to="`/${post.slug}/`"
      >
        <time>{{ date(post.published_at) }}</time>
        <span>{{ post.title }}</span>
      </RouterLink>
    </section>
    <p
      v-if="error"
      class="form-error"
    >
      {{ error }}
    </p>
    <button
      v-if="page < pages || error"
      class="button-secondary"
      :disabled="loading"
      @click="load"
    >
      {{ loading ? 'Loading…' : 'Load more' }}
    </button>
  </main>
</template>
