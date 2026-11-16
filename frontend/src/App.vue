<script setup lang="ts">
import { ref } from 'vue'
import { X, ArrowUpRight, Rss } from 'lucide-vue-next'
import { site } from './stores/site'
import { toast } from './stores/notifications'
import { useBlogNavigation } from './composables/useBlogNavigation'
import { usePageViews } from './composables/usePageViews'
import SearchDialog from './components/SearchDialog.vue'

usePageViews()

const closeButton = ref<HTMLButtonElement>()
const { admin, menu, searching, trap } = useBlogNavigation(closeButton)

function isInternal(url: string): boolean {
  return url.startsWith('/') && !url.startsWith('//') && !url.startsWith('/rss')
}
</script>

<template>
  <a
    class="skip-link"
    href="#main-content"
  >
    Skip to content
  </a>
  <div :inert="menu || searching ? true : undefined"><RouterView /></div>
  <template v-if="!admin">
    <footer class="blog-footer">
      <RouterLink to="/">{{ site.title }}</RouterLink>
      <span>© {{ new Date().getFullYear() }}</span>
      <div>
        <RouterLink to="/archive/">Archive</RouterLink>
        <RouterLink to="/tags/">Tags</RouterLink>
        <a href="/rss/">RSS</a>
      </div>
    </footer>
    <div
      v-if="menu"
      class="drawer-backdrop"
      @click.self="menu = false"
    >
      <aside
        class="menu-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Site navigation"
        @keydown="trap"
      >
        <div class="drawer-heading">
          <span>Menu</span>
          <button
            ref="closeButton"
            class="icon-button"
            aria-label="Close menu"
            @click="menu = false"
          >
            <X :size="22" />
          </button>
        </div>
        <nav>
          <template
            v-for="(item, i) in site.navigation"
            :key="i"
          >
            <RouterLink
              v-if="isInternal(item.url)"
              :to="item.url"
            >
              {{ item.label }}
            </RouterLink>
            <a
              v-else
              :href="item.url"
              :target="item.url.startsWith('http') ? '_blank' : undefined"
              rel="noopener noreferrer"
            >
              {{ item.label }}
              <ArrowUpRight :size="16" />
            </a>
          </template>
        </nav>
        <div class="drawer-bottom">
          <a
            class="rss-link"
            href="/rss/"
          >
            <Rss :size="15" />
            RSS
          </a>
        </div>
      </aside>
    </div>
    <SearchDialog
      v-if="searching"
      @close="searching = false"
    />
  </template>
  <Transition name="toast">
    <div
      v-if="toast"
      role="status"
      class="toast-message"
    >
      {{ toast }}
    </div>
  </Transition>
</template>
