<script setup lang="ts">
import { ref } from 'vue'
import { useCodeCopy } from '../composables/useCodeCopy'
import { useCodeHighlighting } from '../composables/useCodeHighlighting'
import { useArticleImages } from '../composables/useArticleImages'
import ImageLightbox from './ImageLightbox.vue'
import 'prismjs/themes/prism.css'

const props = defineProps<{ html: string }>()
const root = ref<HTMLElement>()
const {
  image,
  open: openImage,
  keyboard: imageKeyboard,
  onImageError,
} = useArticleImages(root, () => props.html)
useCodeHighlighting(root, () => props.html)
const codeCopied = useCodeCopy(root, () => props.html)
</script>
<template>
  <div
    ref="root"
    class="post-content article-body"
    v-html="html"
    @click="openImage"
    @keydown="imageKeyboard"
    @error.capture="onImageError"
  />
  <span
    class="code-copy-status"
    role="status"
  >
    {{ codeCopied ? 'Code copied' : '' }}
  </span>
  <ImageLightbox
    v-if="image"
    :src="image.src"
    :alt="image.alt"
    @close="image = null"
  />
</template>
