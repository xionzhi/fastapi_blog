<script setup lang="ts">
import type { PostSummary as Post } from '../types'
import { date } from '../utils/format'
import { site } from '../stores/site'
defineProps<{ post: Post; compact?: boolean }>()
</script>
<template>
  <div class="post-meta article-meta">
    <template v-if="!compact">
      <img
        v-if="site.author_image"
        class="author-thumb"
        :src="site.author_image"
        :alt="post.author"
        loading="lazy"
        decoding="async"
      />
      <RouterLink :to="`/author/${post.author_slug}/`">{{ post.author }}</RouterLink>
    </template>
    <span
      v-if="post.tags.length"
      class="meta-tags"
    >
      <span v-if="!compact">on</span>
      <template
        v-for="(tag, index) in post.tags"
        :key="tag.id"
      >
        <span v-if="index">,</span>
        <RouterLink :to="`/tag/${tag.slug}/`">{{ tag.name }}</RouterLink>
      </template>
    </span>
    <time
      class="post-date"
      :datetime="post.published_at || undefined"
    >
      {{ date(post.published_at) }}
    </time>
    <span v-if="compact">{{ post.reading_time }} min read</span>
  </div>
</template>
