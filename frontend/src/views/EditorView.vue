<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft, ExternalLink, Images, Send } from 'lucide-vue-next'
import ArticleBody from '../components/ArticleBody.vue'
import PostSettings from '../components/editor/PostSettings.vue'
import ImagePicker from '../components/media/ImagePicker.vue'
import { usePostEditor } from '../composables/usePostEditor'

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
  dirty,
  automaticSlug,
  save,
  load,
} = usePostEditor(textarea)
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
          <div class="segmented">
            <button
              :class="{ active: mode === 'write' }"
              @click="mode = 'write'"
            >
              Edit
            </button>
            <button
              :class="{ active: mode === 'split' }"
              @click="mode = 'split'"
            >
              Split
            </button>
            <button
              :class="{ active: mode === 'preview' }"
              @click="mode = 'preview'"
            >
              Preview
            </button>
          </div>
          <div>
            <button
              class="text-button"
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
      />
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
</style>
