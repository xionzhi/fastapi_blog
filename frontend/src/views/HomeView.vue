<script setup lang="ts">
import { getPosts } from '../api/posts'

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronDown, Search } from 'lucide-vue-next'
import { useAsyncResource } from '../composables/useAsyncResource'
import { usePageMetadata } from '../composables/usePageMetadata'
import { site } from '../stores/site'
import { takeInitialPosts } from '../stores/initial'
import type { Page, PostSummary as Post } from '../types'
import BlogNav from '../components/BlogNav.vue'
import PostMeta from '../components/PostMeta.vue'
import Pagination from '../components/Pagination.vue'
const route = useRoute()
const initialPosts = takeInitialPosts(route.path)
const page = computed(() => Math.max(1, Number(route.params.page) || 1))
const {
  data,
  loading,
  error,
  reload: load,
} = useAsyncResource<Page<Post>>(
  () => route.path,
  (signal) =>
    getPosts(
      {
        page: page.value,
        limit: site.value.posts_per_page,
        tag: String(route.params.tag || ''),
        author: String(route.params.author || ''),
      },
      signal,
    ),
  initialPosts,
)
const title = computed(() =>
  route.params.tag
    ? data.value?.items.flatMap((post) => post.tags).find((tag) => tag.slug === route.params.tag)
        ?.name || route.params.tag
    : route.params.author || site.value.title,
)
usePageMetadata(() => ({
  title: `${route.params.tag || route.params.author ? `${title.value} · ` : ''}${site.value.title}`,
}))
function search() {
  document.dispatchEvent(new Event('blog-search'))
}
</script>
<template>
  <header
    class="main-header blog-hero"
    :class="{ 'collection-hero': route.params.tag || route.params.author, 'no-cover': !site.cover }"
  >
    <img
      v-if="site.cover"
      class="hero-cover"
      :src="site.cover"
      :width="site.images?.cover?.width"
      :height="site.images?.cover?.height"
      alt=""
      aria-hidden="true"
      fetchpriority="high"
      decoding="async"
    />
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
          aria-haspopup="dialog"
          @click="search"
        >
          <Search :size="15" />
          <span>Search posts</span>
          <kbd>Ctrl / ⌘ K</kbd>
        </button>
      </div>
      <div
        class="public-results"
        :aria-busy="loading"
      >
        <p
          v-if="loading"
          class="refresh-status"
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
        <div
          v-if="data && !error"
          :inert="loading ? true : undefined"
        >
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
            <RouterLink
              v-if="page > 1"
              to="/"
            >
              Back to latest posts
            </RouterLink>
          </div>
          <Pagination
            :page="data.page"
            :pages="data.pages"
          />
        </div>
      </div>
    </div>
  </main>
</template>
