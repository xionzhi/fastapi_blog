<script setup lang="ts">
import { checkResetToken, resetPassword } from '../api/auth'
import { clearSession } from '../stores/session'

import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, KeyRound, CheckCircle } from 'lucide-vue-next'
import { errorMessage } from '../utils/format'
import { site } from '../stores/site'
const route = useRoute()
const router = useRouter()
const token = new URLSearchParams(route.hash.slice(1)).get('token') || ''
const valid = ref(false)
const checking = ref(true)
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
const message = ref('')
// Remove the one-time credential from visible history as soon as it is captured.
if (route.hash) router.replace({ path: '/workspace/reset-password', hash: '' })
async function check() {
  try {
    await checkResetToken(token)
    valid.value = true
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    checking.value = false
  }
}
if (token) check()
else {
  checking.value = false
  error.value = 'This reset link is missing or invalid. Please request a new one.'
}
async function submit() {
  if (password.value !== confirmation.value) {
    error.value = 'Passwords do not match.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    message.value = (await resetPassword(token, password.value)).message
    password.value = ''
    confirmation.value = ''
    clearSession()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <main
    id="main-content"
    class="admin login-page"
  >
    <RouterLink
      class="login-back"
      to="/workspace/login"
    >
      <ArrowLeft :size="16" />
      Back to sign in
    </RouterLink>
    <section class="login-card recovery-card">
      <div class="login-icon">
        <CheckCircle
          v-if="message"
          :size="26"
        />
        <KeyRound
          v-else
          :size="26"
        />
      </div>
      <p class="eyebrow">{{ site.title }}</p>
      <h1>{{ message ? 'Password updated.' : 'Set a new password.' }}</h1>
      <p
        v-if="checking"
        class="muted"
        role="status"
      >
        Checking your reset link…
      </p>
      <template v-else-if="message">
        <p
          class="muted"
          role="status"
        >
          {{ message }}
        </p>
        <RouterLink
          class="button-primary"
          to="/workspace/login"
        >
          Sign in
        </RouterLink>
      </template>
      <form
        v-else-if="valid"
        @submit.prevent="submit"
      >
        <p class="muted">Use at least 12 characters. All existing sessions will be signed out.</p>
        <label>
          New password
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            minlength="12"
            maxlength="1024"
            required
          />
        </label>
        <label>
          Confirm new password
          <input
            v-model="confirmation"
            type="password"
            autocomplete="new-password"
            minlength="12"
            maxlength="1024"
            required
          />
        </label>
        <button
          class="button-primary"
          :disabled="busy"
        >
          {{ busy ? 'Updating…' : 'Reset password' }}
        </button>
      </form>
      <p
        v-if="error"
        class="form-error"
        role="alert"
      >
        {{ error }}
      </p>
      <RouterLink
        v-if="!checking && !valid"
        class="button-secondary"
        to="/workspace/forgot-password"
      >
        Request a new link
      </RouterLink>
    </section>
  </main>
</template>
