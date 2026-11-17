<script setup lang="ts">
import { onMounted, ref } from 'vue'

defineProps<{ failed?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const closeButton = ref<HTMLButtonElement>()
onMounted(() => closeButton.value?.focus())
</script>
<template>
  <div
    class="search-backdrop"
    @click.self="emit('close')"
    @keydown.esc.stop.prevent="emit('close')"
  >
    <section
      class="search-dialog"
      role="dialog"
      aria-modal="true"
      aria-label="Search posts"
      @keydown.tab.prevent="closeButton?.focus()"
    >
      <div class="search-field">
        <p :role="failed ? 'alert' : 'status'">
          {{
            failed
              ? 'Search could not load. Check your connection and reload this page.'
              : 'Loading search…'
          }}
        </p>
        <button
          ref="closeButton"
          class="text-button"
          @click="emit('close')"
        >
          Close search
        </button>
      </div>
    </section>
  </div>
</template>
