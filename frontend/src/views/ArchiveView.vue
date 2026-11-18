<script setup lang="ts">
import BlogNav from '../components/BlogNav.vue'
import { date } from '../utils/format'
import { site } from '../stores/site'
import { usePageMetadata } from '../composables/usePageMetadata'
import { useArchive } from '../composables/useArchive'
const { total, page, pages, loading, error, groups, load } = useArchive()
usePageMetadata(() => ({ title: `Archive · ${site.value.title}` }))
</script>
<template>
  <BlogNav />
  <main
    id="main-content"
    class="index-page archive-page"
  >
    <h1>Archive</h1>
    <p
      v-if="total !== undefined"
      class="index-description"
    >
      {{ total }} {{ total === 1 ? 'post' : 'posts' }}
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
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-else-if="total === 0"
      class="muted"
    >
      No posts yet.
    </p>
    <button
      v-if="page < pages || error"
      class="button-secondary"
      :disabled="loading"
      @click="load"
    >
      {{ loading ? 'Loading…' : error ? 'Try again' : 'Load more' }}
    </button>
  </main>
</template>
