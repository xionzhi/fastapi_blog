<script setup lang="ts">
import { ImagePlus, X } from 'lucide-vue-next'
import type { EditorDraft } from '../../composables/usePostEditor'
import type { Tag } from '../../types'

const model = defineModel<EditorDraft>({ required: true })
const tagText = defineModel<string>('tagText', { required: true })
defineProps<{ tags: Tag[]; uploading: boolean }>()
defineEmits<{ uploadCover: []; manualSlug: [] }>()
</script>
<template>
  <aside class="editor-options">
    <h2>Post settings</h2>
    <label>
      Post URL
      <span class="input-prefix">
        /
        <input
          v-model="model.slug"
          @input="$emit('manualSlug')"
          placeholder="article-slug"
          maxlength="200"
        />
      </span>
    </label>
    <label>
      Content type
      <select v-model="model.type">
        <option value="post">Post</option>
        <option value="page">Page</option>
      </select>
    </label>
    <label>
      Tags
      <input
        v-model="tagText"
        list="existing-tags"
        placeholder="python, redis"
      />
      <small>Separate with commas. New tags are created when you save.</small>
    </label>
    <datalist id="existing-tags">
      <option
        v-for="tag in tags"
        :key="tag.id"
        :value="tag.name"
      />
    </datalist>
    <label>
      Excerpt
      <textarea
        v-model="model.excerpt"
        rows="4"
        placeholder="Leave blank for an automatic excerpt"
        maxlength="1000"
      />
    </label>
    <label>
      Cover image
      <input
        v-model="model.feature_image"
        placeholder="Image URL or local path"
      />
      <span
        v-if="model.feature_image"
        class="cover-preview"
      >
        <img
          :src="model.feature_image"
          alt="Cover"
        />
        <button
          class="icon-button"
          @click="model.feature_image = ''"
          aria-label="Remove cover"
        >
          <X :size="16" />
        </button>
      </span>
      <button
        class="button-secondary upload-button"
        type="button"
        :disabled="uploading"
        @click="$emit('uploadCover')"
      >
        <ImagePlus :size="16" />
        {{ uploading ? 'Uploading…' : 'Upload cover' }}
      </button>
    </label>
    <label>
      Author
      <input
        v-model="model.author"
        maxlength="100"
      />
    </label>
    <label>
      Author slug
      <input
        v-model="model.author_slug"
        maxlength="200"
      />
    </label>
    <p class="muted option-note">
      Pages are available at their own URL and do not appear in the home feed.
    </p>
  </aside>
</template>
