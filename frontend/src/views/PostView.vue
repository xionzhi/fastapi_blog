<script setup lang="ts">
import { getDraftPreview, getPost } from '../api/posts'

import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Link, List } from 'lucide-vue-next'
import { useAsyncResource } from '../composables/useAsyncResource'
import { usePageMetadata } from '../composables/usePageMetadata'
import { takeInitialPost } from '../stores/initial'
import { notify } from '../stores/notifications'
import { site } from '../stores/site'
import type { PostDetail as Post } from '../types'
import BlogNav from '../components/BlogNav.vue'
import PostMeta from '../components/PostMeta.vue'
import ArticleBody from '../components/ArticleBody.vue'
const route = useRoute()
const router = useRouter()
const preview = computed(() => route.name === 'draft-preview')
const toc = ref<{ id: string; text: string; level: number }[]>([])
const showToc = ref(false)
const {
  data: loadedPost,
  loading,
  error,
  reload: load,
} = useAsyncResource<Post | undefined>(
  () => route.path,
  async (signal) => {
    if (preview.value) return getDraftPreview(String(route.params.id), signal)
    const data = await getPost(String(route.params.slug), signal)
    if (signal.aborted) return
    if ('redirect' in data) {
      await router.replace(`/${data.redirect}/`)
      return
    }
    return data
  },
  takeInitialPost(route.path),
)
const post = computed(() => {
  const data = loadedPost.value
  if (!data) return undefined
  if (preview.value)
    return data.status === 'draft' && data.id === route.params.id ? data : undefined
  return data.status === 'published' && data.slug === route.params.slug ? data : undefined
})
usePageMetadata(() => {
  const data = post.value
  if (!data || data.slug !== route.params.slug) return {}
  return {
    title: `${data.title} · ${site.value.title}`,
    description:
      data.excerpt ||
      new DOMParser()
        .parseFromString(data.html, 'text/html')
        .body.textContent?.trim()
        .slice(0, 180) ||
      '',
    image: data.feature_image,
    type: 'article',
  }
})
watch(
  post,
  (data) => {
    showToc.value = false
    toc.value = []
    if (!data) return
    const doc = new DOMParser().parseFromString(data.html, 'text/html')
    toc.value = [...doc.querySelectorAll('h1,h2,h3')].map((h) => ({
      id: h.id,
      text: h.textContent || '',
      level: Number(h.tagName[1]),
    }))
  },
  { immediate: true },
)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    notify('Post link copied')
  } catch {
    notify('Please copy the link from the address bar.')
  }
}
</script>
<template>
  <header
    class="main-header post-head article-head"
    :class="{ 'no-cover': !post?.feature_image }"
    :style="post?.feature_image ? { backgroundImage: `url('${post.feature_image}')` } : {}"
  >
    <BlogNav :overlay="!!post?.feature_image" />
  </header>
  <main
    id="main-content"
    class="content public-results"
    :aria-busy="loading"
  >
    <p
      v-if="loading"
      class="refresh-status"
      role="status"
    >
      Loading posts…
    </p>
    <section
      v-if="error"
      class="state-message"
    >
      <h1>{{ preview ? 'Unable to load this preview' : 'Unable to load this post' }}</h1>
      <p>{{ error }}</p>
      <button
        class="button-secondary"
        @click="load"
      >
        Try again
      </button>
      <RouterLink to="/">Back to home</RouterLink>
    </section>
    <article
      v-else-if="post"
      class="post detail-post"
      :inert="loading ? true : undefined"
    >
      <header class="post-header">
        <p
          v-if="preview"
          class="muted"
        >
          Draft preview
        </p>
        <h1 class="post-title">{{ post.title }}</h1>
        <PostMeta
          v-if="post.type === 'post'"
          :post="post"
          compact
        />
      </header>
      <div
        v-if="toc.length > 2"
        class="article-toc"
      >
        <button
          @click="showToc = !showToc"
          :aria-expanded="showToc"
        >
          <List :size="17" />
          On this page
          <span>{{ showToc ? '−' : '+' }}</span>
        </button>
        <nav v-if="showToc">
          <a
            v-for="h in toc"
            :key="h.id"
            :href="`#${h.id}`"
            :style="{ paddingLeft: `${Math.max(0, h.level - 1) * 14}px` }"
          >
            {{ h.text }}
          </a>
        </nav>
      </div>
      <ArticleBody :html="post.html" />
      <footer class="post-footer detail-footer">
        <div>
          <h4>
            <RouterLink :to="`/author/${post.author_slug}/`">{{ post.author }}</RouterLink>
          </h4>
          <p>{{ site.author_bio || 'Notes and discoveries.' }}</p>
        </div>
        <button
          class="text-button"
          @click="copyLink"
        >
          <Link :size="16" />
          Copy link
        </button>
      </footer>
    </article>
  </main>
  <aside
    v-if="post?.related?.length"
    class="related-posts"
  >
    <RouterLink
      v-for="(item, index) in post.related"
      :key="item.id"
      :to="`/${item.slug}/`"
    >
      <span>
        {{ index === 0 ? 'Keep reading' : 'Another story' }}
        <ArrowRight :size="16" />
      </span>
      <h2>{{ item.title }}</h2>
      <p>{{ item.excerpt.slice(0, 90) }}…</p>
    </RouterLink>
  </aside>
</template>
