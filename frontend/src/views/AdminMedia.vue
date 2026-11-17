<script setup lang="ts">
import ImageLibrary from '../components/media/ImageLibrary.vue'
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div>
        <p class="eyebrow">YOUR IMAGE LIBRARY</p>
        <h1>Images</h1>
        <p class="muted">Reuse uploads, manage file paths, and check where images are used.</p>
      </div>
    </header>
    <ImageLibrary />
  </div>
</template>
