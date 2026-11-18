<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft, Copy, ExternalLink, Images, Link2, Link2Off, Send } from 'lucide-vue-next'
import ArticleBody from '../components/ArticleBody.vue'
import PostSettings from '../components/editor/PostSettings.vue'
import ImagePicker from '../components/media/ImagePicker.vue'
import { usePostEditor } from '../composables/usePostEditor'
import { notify } from '../stores/notifications'

const textarea = ref<HTMLTextAreaElement>()
const {
  model,
  id,
  tagText,
  tags,
  mode,
  html,
  loading,
  ready,
  busy,
  libraryOpen,
  openLibrary,
  selectImage,
  error,
  previewError,
  previewing,
  previewShared,
  setPreviewSharing,
  dirty,
  automaticSlug,
  save,
  load,
} = usePostEditor(textarea)

async function copyPreviewLink(): Promise<void> {
  try {
    await navigator.clipboard.writeText(
      new URL(`/preview/${id.value}`, window.location.origin).href,
    )
    notify('Preview link copied')
  } catch {
    notify('Open the preview and copy the link from the address bar.')
  }
}
</script>
<template>
  <div
    class="editor-page"
    @keydown.ctrl.s.prevent="save()"
    @keydown.meta.s.prevent="save()"
  >
    <header class="editor-topbar">
      <RouterLink
        to="/workspace/posts"
        class="text-button"
      >
        <ArrowLeft :size="18" />
        Posts
      </RouterLink>
      <span class="editor-state">
        {{ dirty ? 'Unsaved changes' : id ? 'All changes saved' : 'New post' }}
      </span>
      <div class="editor-actions">
        <a
          v-if="id && model.status === 'published'"
          :href="`/${model.slug}/`"
          target="_blank"
          class="icon-button"
          aria-label="View post"
        >
          <ExternalLink :size="18" />
        </a>
        <button
          class="button-secondary"
          :disabled="busy || loading || !ready"
          @click="save('draft')"
        >
          {{ model.status === 'published' ? 'Unpublish' : 'Save draft' }}
        </button>
        <button
          class="button-primary"
          :disabled="busy || loading || !ready || !model.title.trim()"
          @click="save('published')"
        >
          <Send :size="15" />
          {{ busy ? 'Saving…' : model.status === 'published' ? 'Update post' : 'Publish post' }}
        </button>
      </div>
    </header>
    <p
      v-if="error"
      class="form-error editor-error"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-if="loading"
      class="panel-message"
    >
      Loading editor…
    </p>
    <button
      v-else-if="!ready"
      class="button-secondary"
      @click="load"
    >
      Try again
    </button>
    <div
      v-else
      class="editor-grid"
    >
      <section class="writing-panel">
        <input
          v-model="model.title"
          class="editor-title"
          placeholder="Post title"
          aria-label="Post title"
          maxlength="300"
        />
        <div class="editor-format-bar">
          <div
            class="segmented"
            role="group"
            aria-label="Editor layout"
          >
            <button
              :class="{ active: mode === 'write' }"
              :aria-pressed="mode === 'write'"
              @click="mode = 'write'"
            >
              Edit
            </button>
            <button
              :class="{ active: mode === 'split' }"
              :aria-pressed="mode === 'split'"
              @click="mode = 'split'"
            >
              Split
            </button>
            <button
              :class="{ active: mode === 'preview' }"
              :aria-pressed="mode === 'preview'"
              @click="mode = 'preview'"
            >
              Preview
            </button>
          </div>
          <div>
            <button
              class="text-button"
              aria-haspopup="dialog"
              :disabled="busy"
              @click="openLibrary"
            >
              <Images :size="17" />
              Image library
            </button>
          </div>
        </div>
        <div
          class="writing-area"
          :class="{ split: mode === 'split' }"
        >
          <textarea
            v-show="mode !== 'preview'"
            ref="textarea"
            v-model="model.body"
            :placeholder="
              model.format === 'markdown' ? 'Start writing in Markdown…' : '<p>Start writing…</p>'
            "
            aria-label="Post content"
            spellcheck="false"
          />
          <section
            v-if="mode !== 'write'"
            class="editor-preview"
            :aria-busy="previewing"
          >
            <p
              v-if="previewing"
              class="refresh-status muted"
              role="status"
            >
              Generating preview…
            </p>
            <p
              v-if="previewError"
              class="form-error"
            >
              {{ previewError }}
            </p>
            <ArticleBody
              v-else
              :html="html"
            />
          </section>
        </div>
        <div class="editor-bottom-bar">
          <span>{{ model.body.length }} characters</span>
          <span>Ctrl / ⌘ S Save</span>
        </div>
      </section>
      <PostSettings
        v-model="model"
        v-model:tag-text="tagText"
        :tags="tags"
        :busy="busy"
        @manual-slug="automaticSlug = false"
      >
        <template #preview-sharing>
          <section
            v-if="id && model.status === 'draft'"
            class="preview-sharing"
            aria-labelledby="preview-sharing-title"
          >
            <h2 id="preview-sharing-title">Share draft preview</h2>
            <div class="preview-sharing-actions">
              <template v-if="previewShared">
                <button
                  class="preview-control"
                  :disabled="busy"
                  @click="copyPreviewLink"
                >
                  <Copy :size="15" />
                  Copy link
                </button>
                <a
                  :href="`/preview/${id}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="preview-control preview-control-icon"
                  aria-label="Open preview in a new tab"
                  title="Open preview"
                >
                  <ExternalLink :size="16" />
                </a>
              </template>
              <button
                class="preview-control"
                :class="{ 'preview-control-icon': previewShared }"
                :aria-label="previewShared ? 'Disable preview link' : undefined"
                :title="previewShared ? 'Disable preview link' : undefined"
                :disabled="busy"
                @click="setPreviewSharing(!previewShared)"
              >
                <Link2Off
                  v-if="previewShared"
                  :size="16"
                />
                <template v-else>
                  <Link2 :size="15" />
                  Enable link
                </template>
              </button>
            </div>
          </section>
        </template>
      </PostSettings>
    </div>
    <ImagePicker
      v-if="libraryOpen"
      insert
      @select="selectImage"
      @close="libraryOpen = false"
    />
  </div>
</template>

<style scoped>
.editor-format-bar,
.editor-format-bar > div:last-child {
  flex-wrap: wrap;
}
.preview-sharing {
  display: grid;
  grid-column: 1 / -1;
  gap: 8px;
}
.preview-sharing-actions {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--admin-surface);
}
.preview-control {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--green);
  font-size: 12px;
  text-decoration: none;
}
.preview-control-icon {
  flex: 0 0 40px;
  border-left: 1px solid var(--line);
}
.preview-control:not(:disabled):hover {
  background: var(--admin-panel);
}
.preview-control:focus-visible {
  outline-offset: -3px;
}
</style>
