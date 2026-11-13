<script setup lang="ts">
import { Menu } from 'lucide-vue-next'
import { site } from '../stores/site'
defineProps<{ overlay?: boolean }>()
function openMenu(): void {
  document.dispatchEvent(new Event('blog-menu'))
}
</script>
<template>
  <nav
    class="main-nav blog-nav clearfix"
    :class="{ overlay }"
    aria-label="Main navigation"
  >
    <RouterLink
      v-if="site.logo"
      class="blog-logo"
      to="/"
    >
      <img
        :src="site.logo"
        :alt="site.title"
      />
    </RouterLink>
    <RouterLink
      v-else
      class="brand-text"
      to="/"
    >
      {{ site.title }}
    </RouterLink>
    <div class="nav-actions">
      <button
        class="menu-toggle"
        @click="openMenu"
      >
        <Menu :size="16" />
        <span>Menu</span>
      </button>
    </div>
  </nav>
</template>
