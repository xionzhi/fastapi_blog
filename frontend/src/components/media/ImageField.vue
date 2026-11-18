<script setup lang="ts">
import { ref, useId } from 'vue'
import { Images, X } from 'lucide-vue-next'
import type { LibraryImage } from '../../api/media'
import ImagePicker from './ImagePicker.vue'

const model = defineModel<string>({ required: true })
defineProps<{ label: string; disabled?: boolean; preview?: boolean }>()
const open = ref(false)
const inputId = useId()
function choose(image: LibraryImage): void {
  model.value = image.url
  open.value = false
}
</script>

<template>
  <div class="image-field">
    <label :for="inputId">
      {{ label }}
    </label>
    <span class="image-input">
      <input
        :id="inputId"
        v-model="model"
        :disabled="disabled"
        maxlength="2000"
        placeholder="/content/images/…"
      />
      <button
        type="button"
        class="icon-button"
        aria-haspopup="dialog"
        :aria-label="`Choose ${label.toLowerCase()}`"
        title="Choose from image library"
        :disabled="disabled"
        @click="open = true"
      >
        <Images :size="18" />
      </button>
    </span>
    <span
      v-if="preview && model"
      class="cover-preview"
    >
      <img
        :src="model"
        :alt="label"
      />
      <button
        type="button"
        class="icon-button"
        :aria-label="`Remove ${label.toLowerCase()}`"
        :disabled="disabled"
        @click="model = ''"
      >
        <X :size="16" />
      </button>
    </span>
    <ImagePicker
      v-if="open"
      @select="choose"
      @close="open = false"
    />
  </div>
</template>

<style scoped>
.image-field {
  min-width: 0;
  display: grid;
  gap: 8px;
}
.cover-preview {
  margin-top: 0;
}
.image-input {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--admin-surface);
}
.image-input:focus-within {
  border-color: var(--green);
  outline: 2px solid var(--green);
  outline-offset: 2px;
}
.admin .image-field .image-input > input {
  flex: 1;
  width: 0;
  min-width: 0;
  border: 0;
  border-radius: 4px 0 0 4px;
  background: transparent;
}
.image-input > :is(input, button):focus {
  outline: none;
}
.image-input > button {
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border: 0;
  border-left: 1px solid var(--line);
  border-radius: 0 4px 4px 0;
  background: transparent;
  color: var(--green);
}
.image-input > button:not(:disabled):is(:hover, :focus-visible) {
  background: var(--admin-selected);
}
@media (forced-colors: active) {
  .image-input > button:focus-visible {
    outline: 2px solid Highlight;
    outline-offset: -3px;
  }
}
</style>
