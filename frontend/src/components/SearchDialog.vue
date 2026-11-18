<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Search, X, ArrowUpRight } from 'lucide-vue-next'
import { usePostSearch } from '../composables/usePostSearch'
import { useModalFocus } from '../composables/useModalFocus'
const emit = defineEmits<{ close: [] }>()
const active = ref(false)
const dialog = ref<HTMLElement>()
const { query, results, total, loading, error } = usePostSearch()
const { keyboard } = useModalFocus(active, dialog, () => emit('close'))
onMounted(() => {
  active.value = true
})
</script>
<template>
  <Teleport to="body">
    <div
      class="search-backdrop"
      @click.self="$emit('close')"
    >
      <section
        ref="dialog"
        class="search-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Search posts"
        tabindex="-1"
        @keydown="keyboard"
      >
        <div class="search-field">
          <Search :size="22" />
          <input
            v-model="query"
            placeholder="Search posts…"
            aria-label="Search keywords"
          />
          <button
            class="icon-button"
            aria-label="Close search"
            @click="$emit('close')"
          >
            <X :size="20" />
          </button>
        </div>
        <div
          v-if="query.trim()"
          class="search-results"
          aria-live="polite"
          :aria-busy="loading"
        >
          <p
            v-if="loading"
            class="muted"
          >
            Searching…
          </p>
          <p
            v-else-if="error"
            class="form-error"
          >
            {{ error }}
          </p>
          <template v-else>
            <p
              v-if="total"
              class="search-count"
            >
              {{ total }} {{ total === 1 ? 'post' : 'posts' }}
              <span v-if="total > 30">· Showing the first 30</span>
            </p>
            <RouterLink
              v-for="post in results"
              :key="post.id"
              :to="`/${post.slug}/`"
              @click.left.exact="$emit('close')"
            >
              <h3>
                {{ post.title }}
                <ArrowUpRight :size="18" />
              </h3>
              <p>{{ post.excerpt.slice(0, 100) }}</p>
            </RouterLink>
            <p
              v-if="!results.length"
              class="muted"
            >
              No matching posts. Try another search.
            </p>
          </template>
        </div>
        <div class="search-hint">
          <kbd>esc</kbd>
          Close
        </div>
      </section>
    </div>
  </Teleport>
</template>
