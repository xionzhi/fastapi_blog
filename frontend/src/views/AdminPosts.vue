<script setup lang="ts">
import { nextTick, ref } from 'vue'
import {
  Plus,
  Search,
  ArrowLeft,
  ArrowRight,
  FileText,
  Trash2,
  ExternalLink,
} from 'lucide-vue-next'
import { date } from '../utils/format'
import { usePostList } from '../composables/usePostList'
import ConfirmDialog from '../components/ConfirmDialog.vue'
const {
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
} = usePostList()
const heading = ref<HTMLElement>()
async function confirmDelete(): Promise<void> {
  await remove()
  if (deleteTarget.value) return
  await nextTick()
  heading.value?.querySelector('a')?.focus({ preventScroll: true })
}
</script>
<template>
  <div class="admin-page">
    <header
      ref="heading"
      class="admin-page-heading"
    >
      <h1>Posts</h1>
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
        <div
          class="tabs"
          role="group"
          aria-label="Post status"
        >
          <button
            :class="{ active: !status }"
            :aria-pressed="!status"
            :disabled="busy"
            @click="status = ''"
          >
            All
          </button>
          <button
            :class="{ active: status === 'published' }"
            :aria-pressed="status === 'published'"
            :disabled="busy"
            @click="status = 'published'"
          >
            Published
          </button>
          <button
            :class="{ active: status === 'draft' }"
            :aria-pressed="status === 'draft'"
            :disabled="busy"
            @click="status = 'draft'"
          >
            Drafts
          </button>
        </div>
        <label class="table-search">
          <Search :size="16" />
          <input
            v-model="q"
            :disabled="busy"
            placeholder="Search posts…"
            aria-label="Search all posts"
          />
        </label>
      </div>
      <div
        class="post-results"
        role="region"
        aria-label="Post results"
        :aria-busy="loading"
      >
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
          class="post-loading muted"
          role="status"
        >
          Loading…
        </p>
        <div
          v-if="data?.items.length"
          class="post-table"
          :inert="loading || busy ? true : undefined"
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
                :disabled="busy || loading"
                @click="askDelete(post)"
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
          <h3>{{ q.trim() || status ? 'No matching posts' : 'No posts yet' }}</h3>
          <p>
            {{
              q.trim() || status
                ? 'Try another search or filter.'
                : 'Start with an idea. Write your first post.'
            }}
          </p>
          <RouterLink
            v-if="!q.trim() && !status"
            to="/workspace/posts/new"
          >
            Start writing →
          </RouterLink>
        </div>
        <div
          v-if="data && data.pages > 1"
          class="admin-pagination"
        >
          <span>{{ data.total }} posts · Page {{ data.page }} of {{ data.pages }}</span>
          <button
            class="icon-button"
            :disabled="loading || busy || page <= 1"
            @click="page--"
            aria-label="Previous page"
          >
            <ArrowLeft :size="17" />
          </button>
          <button
            class="icon-button"
            :disabled="loading || busy || page >= data.pages"
            @click="page++"
            aria-label="Next page"
          >
            <ArrowRight :size="17" />
          </button>
        </div>
      </div>
    </div>
    <ConfirmDialog
      v-if="deleteTarget"
      title="Delete post?"
      :item-name="deleteTarget.title"
      description="This post will be permanently deleted. This cannot be undone."
      confirm-label="Delete post"
      :busy="busy"
      :error="deleteError"
      @cancel="cancelDelete"
      @confirm="confirmDelete"
    />
  </div>
</template>
