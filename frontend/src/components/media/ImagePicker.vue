<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { LibraryImage } from '../../api/media'
import { useModalFocus } from '../../composables/useModalFocus'
import { useScrollLock } from '../../composables/useScrollLock'
import { imageAlt } from '../../utils/images'
import ImageLibrary from './ImageLibrary.vue'

defineProps<{ insert?: boolean }>()
const emit = defineEmits<{ select: [image: LibraryImage, alt: string]; close: [] }>()
const active = ref(false)
const dialog = ref<HTMLElement>()
const selected = ref<LibraryImage>()
const alt = ref('')
const busy = ref(false)
const loading = ref(true)
onMounted(() => {
  active.value = true
})
useScrollLock(active)
function close(): void {
  if (!busy.value) emit('close')
}
const { keyboard } = useModalFocus(active, dialog, close)
function choose(image: LibraryImage | undefined): void {
  if (image?.path !== selected.value?.path) alt.value = image ? imageAlt(image) : ''
  selected.value = image
}
</script>

<template>
  <Teleport to="body">
    <div
      class="admin admin-modal-backdrop"
      @click.self="close"
      @keydown="keyboard"
    >
      <section
        ref="dialog"
        class="admin-modal image-picker"
        role="dialog"
        aria-modal="true"
        aria-labelledby="image-picker-title"
        tabindex="-1"
      >
        <header>
          <h2 id="image-picker-title">Image library</h2>
          <button
            type="button"
            class="icon-button"
            aria-label="Close image library"
            :disabled="busy"
            @click="close"
          >
            <X :size="20" />
          </button>
        </header>
        <div class="image-picker-scroll">
          <ImageLibrary
            picker
            @select="choose"
            @busy="busy = $event"
            @loading="loading = $event"
          />
        </div>
        <footer>
          <label v-if="insert">
            Alternative text
            <input
              v-model="alt"
              maxlength="300"
              placeholder="Describe the image"
            />
          </label>
          <p class="muted">{{ selected?.path || 'Select an image to continue.' }}</p>
          <div class="picker-actions">
            <button
              type="button"
              class="button-secondary"
              :disabled="busy"
              @click="close"
            >
              Cancel
            </button>
            <button
              type="button"
              class="button-primary"
              :disabled="!selected || busy || loading"
              @click="selected && emit('select', selected, alt)"
            >
              {{ insert ? 'Insert image' : 'Use image' }}
            </button>
          </div>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.image-picker {
  max-width: 1000px;
  max-height: calc(100dvh - 50px);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.image-picker-scroll {
  overflow: auto;
  min-height: 0;
  padding: 2px;
}
.image-picker footer {
  flex-shrink: 0;
  padding-top: 18px;
  border-top: 1px solid #dfe5de;
  margin-top: 18px;
}
.image-picker footer p {
  overflow-wrap: anywhere;
  margin: 10px 0;
}
.picker-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
@media (max-width: 600px) {
  .image-picker {
    padding: 18px;
  }
}
</style>
