<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { notify } from '../stores/notifications'
import { useCodeHighlighting } from '../composables/useCodeHighlighting'
import 'prismjs/themes/prism.css'

const props = defineProps<{ html: string }>()
const root = ref<HTMLElement>()
const lightbox = ref('')
useCodeHighlighting(root, () => props.html)
function click(e: MouseEvent): void {
  const target = e.target as HTMLElement
  if (target.tagName === 'IMG') {
    e.preventDefault()
    lightbox.value = (target as HTMLImageElement).src
  }
}
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
      class="image-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Image preview"
      tabindex="0"
      @click="lightbox = ''"
      @keydown.esc="lightbox = ''"
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
