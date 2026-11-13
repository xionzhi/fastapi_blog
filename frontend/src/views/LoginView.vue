<script setup lang="ts">
import { signIn, getRecoveryStatus } from '../api/auth'
import { applySession } from '../stores/session'

import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, PenLine } from 'lucide-vue-next'
import { errorMessage } from '../utils/format'
import { site } from '../stores/site'
const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
const recoveryEnabled = ref(false)
getRecoveryStatus()
  .then((r) => (recoveryEnabled.value = r.enabled))
  .catch(() => {})
const route = useRoute()
const router = useRouter()
async function login() {
  busy.value = true
  error.value = ''
  try {
    const user = await signIn({ username: username.value, password: password.value })
    applySession(user)
    password.value = ''
    const next =
      typeof route.query.next === 'string' &&
      route.query.next.startsWith('/workspace/') &&
      route.query.next !== '/workspace/login'
        ? route.query.next
        : '/workspace/posts'
    await router.push(next)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
document.title = `Sign in · ${site.value.title}`
</script>
<template>
  <main
    id="main-content"
    class="admin login-page"
  >
    <RouterLink
      class="login-back"
      to="/"
    >
      <ArrowLeft :size="16" />
      Back to blog
    </RouterLink>
    <section class="login-card">
      <div class="login-icon"><PenLine :size="26" /></div>
      <p class="eyebrow">{{ site.title }}</p>
      <h1>Keep writing.</h1>
      <p class="muted">Sign in to your writing workspace</p>
      <form @submit.prevent="login">
        <label>
          Username
          <input
            v-model="username"
            autocomplete="username"
            required
            autofocus
            maxlength="80"
          />
        </label>
        <label>
          Password
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            maxlength="1024"
          />
        </label>
        <p
          v-if="error"
          class="form-error"
          role="alert"
        >
          {{ error }}
        </p>
        <button
          class="button-primary"
          :disabled="busy"
        >
          {{ busy ? 'Signing in…' : 'Sign in' }}
          <ArrowRight :size="17" />
        </button>
      </form>
      <RouterLink
        v-if="recoveryEnabled"
        class="forgot-link"
        to="/workspace/forgot-password"
      >
        Forgot your password?
      </RouterLink>
      <p
        v-else
        class="recovery-disabled"
      >
        Email recovery is not enabled.
      </p>
    </section>
    <p class="login-footnote">A thought today. A story tomorrow.</p>
  </main>
</template>
