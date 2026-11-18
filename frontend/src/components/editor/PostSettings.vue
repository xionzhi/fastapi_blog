<script setup lang="ts">
import ImageField from '../media/ImageField.vue'
import type { EditorDraft } from '../../composables/usePostEditor'
import type { Tag } from '../../types'

const model = defineModel<EditorDraft>({ required: true })
const tagText = defineModel<string>('tagText', { required: true })
defineProps<{ tags: Tag[]; busy: boolean }>()
defineEmits<{ manualSlug: [] }>()
</script>
<template>
  <aside class="editor-options">
    <h2>Post settings</h2>
    <label>
      Post URL
      <span class="input-prefix">
        /
        <input
          v-model.trim="model.slug"
          @input="$emit('manualSlug')"
          placeholder="article-slug"
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
    <ImageField
      v-model="model.feature_image"
      label="Cover image"
      :disabled="busy"
      preview
    />
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
    <slot name="preview-sharing" />
  </aside>
</template>
