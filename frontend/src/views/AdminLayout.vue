<script setup lang="ts">
import { signOut } from '../api/auth'
import { clearSession } from '../stores/session'

import { useRouter } from 'vue-router'
import {
  FileText,
  Tags,
  Image,
  Settings,
  ExternalLink,
  LogOut,
  PenLine,
  BarChart3,
} from 'lucide-vue-next'
import { errorMessage } from '../utils/format'
import { notify } from '../stores/notifications'
import { session } from '../stores/session'
import { site } from '../stores/site'
const router = useRouter()
async function logout() {
  try {
    await signOut()
    clearSession()
    await router.push('/workspace/login')
  } catch (e) {
    notify(errorMessage(e))
  }
}
</script>
<template>
  <div class="admin admin-shell">
    <aside class="admin-sidebar">
      <RouterLink
        class="admin-brand"
        to="/workspace/posts"
      >
        <span class="admin-brand-icon"><PenLine :size="20" /></span>
        <div>
          {{ site.title }}
          <small>Writing workspace</small>
        </div>
      </RouterLink>
      <nav aria-label="Workspace navigation">
        <RouterLink to="/workspace/posts">
          <FileText :size="18" />
          Posts
        </RouterLink>
        <RouterLink to="/workspace/tags">
          <Tags :size="18" />
          Tags
        </RouterLink>
        <RouterLink to="/workspace/images">
          <Image :size="18" />
          Images
        </RouterLink>
        <RouterLink to="/workspace/settings">
          <Settings :size="18" />
          Settings
        </RouterLink>
        <RouterLink to="/workspace/analytics">
          <BarChart3 :size="18" />
          Analytics
        </RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <a
          href="/"
          target="_blank"
        >
          <ExternalLink :size="16" />
          View blog
        </a>
        <button @click="logout">
          <LogOut :size="16" />
          Sign out
          <span>{{ session.username }}</span>
        </button>
      </div>
    </aside>
    <main
      id="main-content"
      class="admin-main"
    >
      <RouterView />
    </main>
  </div>
</template>
