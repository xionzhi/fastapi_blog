<script setup lang="ts">
import { getPublicTags } from '../api/tags'

import { ref } from 'vue'
import BlogNav from '../components/BlogNav.vue'
import { errorMessage } from '../utils/format'
import { site } from '../stores/site'
import type { Tag } from '../types'
const tags = ref<Tag[]>([])
const error = ref('')
getPublicTags()
  .then((v) => (tags.value = v))
  .catch((e) => (error.value = errorMessage(e)))
document.title = `Tags · ${site.value.title}`
</script>
<template>
  <BlogNav />
  <main
    id="main-content"
    class="index-page"
  >
    <p class="eyebrow">TOPICS</p>
    <h1>Tags</h1>
    <p class="index-description">Follow a topic. Keep exploring.</p>
    <p
      v-if="error"
      class="form-error"
    >
      {{ error }}
    </p>
    <div class="tag-cloud">
      <RouterLink
        v-for="tag in tags"
        :key="tag.id"
        :to="`/tag/${tag.slug}/`"
      >
        {{ tag.name }}
        <span>{{ tag.count }}</span>
      </RouterLink>
    </div>
  </main>
</template>
