<script setup lang="ts">
import { ref } from 'vue'
import { notify } from '../stores/notifications'
import { useCodeHighlighting } from '../composables/useCodeHighlighting'
import { useArticleImages } from '../composables/useArticleImages'
import ImageLightbox from './ImageLightbox.vue'
import 'prismjs/themes/prism.css'

const props = defineProps<{ html: string }>()
const root = ref<HTMLElement>()
const { image, open: openImage, keyboard: imageKeyboard } = useArticleImages(root, () => props.html)
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
    @click="openImage"
    @keydown="imageKeyboard"
    @dblclick="copy"
  />
  <p
    v-if="html.includes('<pre')"
    class="code-hint"
  >
    Double-click a code block to copy it
  </p>
  <ImageLightbox
    v-if="image"
    :src="image.src"
    :alt="image.alt"
    @close="image = null"
  />
</template>
