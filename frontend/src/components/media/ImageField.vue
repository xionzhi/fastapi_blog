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
}
.admin .image-input input {
  flex: 1;
  width: 0;
  min-width: 0;
  border-radius: 5px 0 0 5px;
}
.image-input button {
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border: 1px solid #dfe5de;
  border-left: 0;
  border-radius: 0 5px 5px 0;
  background: #fff;
  color: var(--green);
}
</style>
