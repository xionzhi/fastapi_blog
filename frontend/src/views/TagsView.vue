<script setup lang="ts">
import { getPublicTags } from '../api/tags'

import BlogNav from '../components/BlogNav.vue'
import { site } from '../stores/site'
import { usePageMetadata } from '../composables/usePageMetadata'
import { useAsyncResource } from '../composables/useAsyncResource'
const { data: tags, loading, error, reload } = useAsyncResource(() => true, getPublicTags)
usePageMetadata(() => ({ title: `Tags · ${site.value.title}` }))
</script>
<template>
  <BlogNav />
  <main
    id="main-content"
    class="index-page"
  >
    <h1>Tags</h1>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
      <button
        type="button"
        class="text-button"
        @click="reload"
      >
        Try again
      </button>
    </p>
    <p
      v-if="loading"
      class="muted"
      role="status"
    >
      Loading tags…
    </p>
    <p
      v-else-if="!error && !tags?.length"
      class="muted"
    >
      No tags yet.
    </p>
    <div
      class="tag-cloud"
      :aria-busy="loading"
      :inert="loading ? true : undefined"
    >
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
