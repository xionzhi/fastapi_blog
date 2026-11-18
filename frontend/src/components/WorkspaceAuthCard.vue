<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import { site } from '../stores/site'

withDefaults(
  defineProps<{ title: string; backTo?: string; backLabel?: string; recovery?: boolean }>(),
  {
    backTo: '/workspace/login',
    backLabel: 'Back to sign in',
  },
)
</script>

<template>
  <main
    id="main-content"
    class="admin login-page"
  >
    <RouterLink
      class="login-back"
      :to="backTo"
    >
      <ArrowLeft :size="16" />
      {{ backLabel }}
    </RouterLink>
    <section
      class="login-card"
      :class="{ 'recovery-card': recovery }"
    >
      <div
        class="login-icon"
        aria-hidden="true"
      >
        <slot name="icon" />
      </div>
      <p class="eyebrow">{{ site.title }}</p>
      <h1>{{ title }}</h1>
      <slot />
    </section>
  </main>
</template>
