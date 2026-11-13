<script setup lang="ts">
import BlogNav from '../components/BlogNav.vue'
</script>
<template>
  <BlogNav />
  <main
    id="main-content"
    class="state-message not-found"
  >
    <p>404</p>
    <h1>Page not found</h1>
    <p>Try searching, or return home to keep reading.</p>
    <RouterLink
      class="button-secondary"
      to="/"
    >
      Back to home
    </RouterLink>
  </main>
</template>
