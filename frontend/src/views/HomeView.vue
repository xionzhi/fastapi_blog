<script setup lang="ts">
import { getPosts } from '../api/posts'
import { getPublicTags } from '../api/tags'

import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronDown, Search } from 'lucide-vue-next'
import { errorMessage } from '../utils/format'
import { site } from '../stores/site'
import type { Page, PostSummary as Post, Tag } from '../types'
import BlogNav from '../components/BlogNav.vue'
import PostMeta from '../components/PostMeta.vue'
import Pagination from '../components/Pagination.vue'
const route = useRoute()
const data = ref<Page<Post>>()
const loading = ref(true)
const error = ref('')
const tags = ref<Tag[]>([])
const page = computed(() => Math.max(1, Number(route.params.page) || 1))
const title = computed(() =>
  route.params.tag
    ? tags.value.find((t) => t.slug === route.params.tag)?.name || route.params.tag
    : route.params.author || site.value.title,
)
let seq = 0
async function load() {
  const id = ++seq
  loading.value = true
  error.value = ''
  try {
    const result = await getPosts({
      page: page.value,
      limit: site.value.posts_per_page,
      tag: String(route.params.tag || ''),
      author: String(route.params.author || ''),
    })
    if (id === seq) data.value = result
  } catch (e) {
    if (id === seq) error.value = errorMessage(e)
  } finally {
    if (id === seq) loading.value = false
  }
  document.title = `${route.params.tag || route.params.author ? `${title.value} · ` : ''}${site.value.title}`
}
getPublicTags()
  .then((v) => (tags.value = v))
  .catch(() => {})
watch(() => route.fullPath, load, { immediate: true })
function search() {
  document.dispatchEvent(new Event('blog-search'))
}
</script>
<template>
  <header
    class="main-header blog-hero"
    :class="{ 'collection-hero': route.params.tag || route.params.author, 'no-cover': !site.cover }"
    :style="site.cover ? { backgroundImage: `url('${site.cover}')` } : {}"
  >
    <BlogNav overlay />
    <div class="hero-shade" />
    <div class="vertical">
      <div class="main-header-content inner">
        <h1 class="page-title">{{ title }}</h1>
        <h2
          v-if="route.params.tag || route.params.author"
          class="page-description"
        >
          {{ data?.total || 0 }} posts
        </h2>
        <h2
          v-else-if="site.description"
          class="page-description"
        >
          {{ site.description }}
        </h2>
      </div>
    </div>
    <a
      v-if="!route.params.tag && !route.params.author"
      class="hero-scroll"
      href="#content"
      aria-label="Scroll to posts"
    >
      <ChevronDown :size="27" />
    </a>
  </header>
  <main id="main-content">
    <div
      id="content"
      class="content post-list"
    >
      <div class="list-tools">
        <span>
          {{
            route.params.tag
              ? 'Posts by tag'
              : route.params.author
                ? 'Posts by author'
                : 'Latest posts'
          }}
          <small v-if="data">/ {{ data.total }}</small>
        </span>
        <button
          class="text-button"
          @click="search"
        >
          <Search :size="15" />
          <span>Search posts</span>
          <kbd>⌘ K</kbd>
        </button>
      </div>
      <p
        v-if="loading"
        class="state-message"
        role="status"
      >
        Loading posts…
      </p>
      <div
        v-else-if="error"
        class="state-message"
      >
        <p>{{ error }}</p>
        <button
          class="button-secondary"
          @click="load"
        >
          Reload
        </button>
      </div>
      <template v-else-if="data">
        <article
          v-for="post in data.items"
          :key="post.id"
          class="post list-post"
        >
          <header class="post-header">
            <h2 class="post-title">
              <RouterLink :to="`/${post.slug}/`">{{ post.title }}</RouterLink>
            </h2>
          </header>
          <section class="post-excerpt">
            <p>
              {{ post.excerpt }}
              <RouterLink
                class="read-more"
                :to="`/${post.slug}/`"
                :aria-label="`Read ${post.title}`"
              >
                »
              </RouterLink>
            </p>
          </section>
          <PostMeta :post="post" />
        </article>
        <div
          v-if="!data.items.length"
          class="state-message"
        >
          <p>{{ page > data.pages ? 'No posts on this page.' : 'No posts yet.' }}</p>
          <RouterLink to="/">Back to home</RouterLink>
        </div>
        <Pagination
          :page="page"
          :pages="data.pages"
        />
      </template>
    </div>
  </main>
</template>
