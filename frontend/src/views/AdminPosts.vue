<script setup lang="ts">
import { deletePost, getAdminPosts, getPostStatistics, type PostStatistics } from '../api/posts'

import { ref, watch } from 'vue'
import {
  Plus,
  Search,
  ArrowLeft,
  ArrowRight,
  FileText,
  Trash2,
  ExternalLink,
} from 'lucide-vue-next'
import { date, errorMessage } from '../utils/format'
import { notify } from '../stores/notifications'
import { useDebouncedTask } from '../composables/useDebouncedTask'
import type { Page, AdminPostSummary as Post } from '../types'
const data = ref<Page<Post>>()
const stats = ref<PostStatistics>({ total: 0, draft: 0, published: 0, tags: 0 })
const q = ref('')
const status = ref('')
const page = ref(1)
const loading = ref(false)
const error = ref('')
let seq = 0
const searchTask = useDebouncedTask(250)
async function load() {
  const id = ++seq
  loading.value = true
  error.value = ''
  try {
    const [posts, counts] = await Promise.all([
      getAdminPosts({ page: page.value, q: q.value, status: status.value }),
      getPostStatistics(),
    ])
    if (id === seq) {
      data.value = posts
      stats.value = counts
    }
  } catch (e) {
    if (id === seq) error.value = errorMessage(e)
  } finally {
    if (id === seq) loading.value = false
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
async function remove(post: Post) {
  if (!confirm(`Delete "${post.title}"? This cannot be undone.`)) return
  try {
    await deletePost(post.id)
    notify('Post deleted')
    if (data.value?.items.length === 1 && page.value > 1) page.value--
    else await load()
  } catch (e) {
    notify(errorMessage(e))
  }
}
load()
</script>
<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div>
        <p class="eyebrow">YOUR STORIES</p>
        <h1>Posts</h1>
        <p class="muted">A home for your thoughts and the stories behind them.</p>
      </div>
      <RouterLink
        class="button-primary"
        to="/workspace/posts/new"
      >
        <Plus :size="17" />
        New post
      </RouterLink>
    </header>
    <div class="stats-row">
      <div>
        <span>All content</span>
        <strong>{{ stats.total || 0 }}</strong>
      </div>
      <div>
        <span>Published</span>
        <strong>{{ stats.published || 0 }}</strong>
      </div>
      <div>
        <span>Drafts</span>
        <strong>{{ stats.draft || 0 }}</strong>
      </div>
      <div>
        <span>Tags</span>
        <strong>{{ stats.tags || 0 }}</strong>
      </div>
    </div>
    <div class="content-panel">
      <div class="table-toolbar">
        <div class="tabs">
          <button
            :class="{ active: !status }"
            @click="status = ''"
          >
            All
          </button>
          <button
            :class="{ active: status === 'published' }"
            @click="status = 'published'"
          >
            Published
          </button>
          <button
            :class="{ active: status === 'draft' }"
            @click="status = 'draft'"
          >
            Drafts
          </button>
        </div>
        <label class="table-search">
          <Search :size="16" />
          <input
            v-model="q"
            placeholder="Search posts…"
            aria-label="Search all posts"
          />
        </label>
      </div>
      <p
        v-if="error"
        class="form-error panel-message"
        role="alert"
      >
        {{ error }}
        <button
          class="text-button"
          @click="load"
        >
          Try again
        </button>
      </p>
      <p
        v-if="loading"
        class="panel-message muted"
        role="status"
      >
        Loading…
      </p>
      <div
        v-else-if="data?.items.length"
        class="post-table"
      >
        <div class="table-label">
          <span>Title</span>
          <span>Status</span>
          <span>Date</span>
          <span>Actions</span>
        </div>
        <div
          v-for="post in data.items"
          :key="post.id"
          class="post-table-row"
        >
          <RouterLink
            :to="`/workspace/posts/${post.id}`"
            class="post-table-title"
          >
            <FileText :size="19" />
            <div>
              <strong>{{ post.title }}</strong>
              <small>
                <span v-if="post.type === 'page'">Page ·</span>
                {{ post.tags.map((t) => t.name).join(' · ') || 'Uncategorized' }}
              </small>
            </div>
          </RouterLink>
          <span>
            <span
              class="status-badge"
              :class="post.status"
            >
              {{
                post.status === 'draft'
                  ? 'Draft'
                  : post.published_at && new Date(post.published_at) > new Date()
                    ? 'Scheduled'
                    : 'Published'
              }}
            </span>
          </span>
          <time>{{ date(post.published_at || post.created_at) }}</time>
          <div class="row-actions">
            <a
              v-if="post.status === 'published'"
              :href="`/${post.slug}/`"
              target="_blank"
              class="icon-button"
              aria-label="View post"
            >
              <ExternalLink :size="16" />
            </a>
            <button
              class="icon-button danger-hover"
              :aria-label="`Delete ${post.title}`"
              @click="remove(post)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
      </div>
      <div
        v-else-if="!loading && !error"
        class="empty-state"
      >
        <FileText :size="32" />
        <h3>No posts yet</h3>
        <p>Start with an idea. Write your first post.</p>
        <RouterLink to="/workspace/posts/new">Start writing →</RouterLink>
      </div>
      <div
        v-if="data && data.pages > 1"
        class="admin-pagination"
      >
        <span>{{ data.total }} posts · Page {{ page }} of {{ data.pages }}</span>
        <button
          class="icon-button"
          :disabled="page <= 1"
          @click="page--"
          aria-label="Previous page"
        >
          <ArrowLeft :size="17" />
        </button>
        <button
          class="icon-button"
          :disabled="page >= data.pages"
          @click="page++"
          aria-label="Next page"
        >
          <ArrowRight :size="17" />
        </button>
      </div>
    </div>
  </div>
</template>
