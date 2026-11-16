<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { notify } from '../stores/notifications'
import { useCodeHighlighting } from '../composables/useCodeHighlighting'
import { useImageLightbox } from '../composables/useImageLightbox'
import 'prismjs/themes/prism.css'

const props = defineProps<{ html: string }>()
const root = ref<HTMLElement>()
const { image: lightbox, dialog, open: click } = useImageLightbox(() => props.html)
useCodeHighlighting(root, () => props.html)
async function copy(e: MouseEvent) {
  const pre = (e.target as HTMLElement).closest('pre')
  if (!pre) return
  try {
    await navigator.clipboard.writeText(pre.innerText)
    notify('Code copied')
  } catch {
    notify('Clipboard access is unavailable. Please copy manually.')
  }
}
</script>
<template>
  <div
    ref="root"
    class="post-content article-body"
    v-html="html"
    @click="click"
    @dblclick="copy"
  />
  <p
    v-if="html.includes('<pre')"
    class="code-hint"
  >
    Double-click a code block to copy it
  </p>
  <Teleport to="body">
    <div
      v-if="lightbox"
      ref="dialog"
      class="image-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Image preview"
      tabindex="0"
      @click="lightbox = ''"
      @keydown.esc.stop.prevent="lightbox = ''"
      @keydown.tab.prevent
      @keydown.ctrl.k.stop.prevent
      @keydown.meta.k.stop.prevent
    >
      <button
        class="icon-button"
        aria-label="Close image"
        autofocus
        @click="lightbox = ''"
      >
        <X />
      </button>
      <img
        :src="lightbox"
        alt="Enlarged image"
      />
    </div>
  </Teleport>
</template>
