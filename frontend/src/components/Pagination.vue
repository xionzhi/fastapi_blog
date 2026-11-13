<script setup lang="ts">
import { useRoute } from 'vue-router'
import { ArrowLeft, ArrowRight } from 'lucide-vue-next'
defineProps<{ page: number; pages: number }>()
const route = useRoute()
function href(page: number) {
  const base = route.params.tag
    ? `/tag/${route.params.tag}`
    : route.params.author
      ? `/author/${route.params.author}`
      : ''
  return page === 1 ? `${base}/` : `${base}/page/${page}/`
}
</script>
<template>
  <nav
    v-if="pages > 1"
    class="pagination blog-pagination"
    aria-label="Post pagination"
  >
    <RouterLink
      v-if="page > 1"
      class="newer-posts"
      :to="href(page - 1)"
    >
      <ArrowLeft :size="14" />
      Newer Posts
    </RouterLink>
    <span class="page-number">Page {{ page }} of {{ pages }}</span>
    <RouterLink
      v-if="page < pages"
      class="older-posts"
      :to="href(page + 1)"
    >
      Older Posts
      <ArrowRight :size="14" />
    </RouterLink>
  </nav>
</template>
