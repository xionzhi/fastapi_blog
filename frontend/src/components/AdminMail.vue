<script setup lang="ts">
import { ref } from 'vue'
import { Mail } from 'lucide-vue-next'
import { getMailStatus, sendTestEmail } from '../api/mail'
import { errorMessage } from '../utils/format'
import { notify } from '../stores/notifications'
const state = ref<{ enabled: boolean; email: string }>()
const error = ref('')
const busy = ref(false)
getMailStatus()
  .then((v) => (state.value = v))
  .catch((e) => (error.value = errorMessage(e)))
async function testMail() {
  busy.value = true
  error.value = ''
  try {
    const r = await sendTestEmail()
    notify(r.message)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <section class="content-panel settings-section mail-section">
    <p class="eyebrow">ACCOUNT SECURITY</p>
    <h2>Administrator email</h2>
    <p class="muted">
      Password reset links and password change notifications are sent to your recovery address.
    </p>
    <template v-if="state">
      <dl class="mail-status">
        <div>
          <dt>Email service</dt>
          <dd>
            <span
              class="status-badge"
              :class="state.enabled ? 'published' : 'draft'"
            >
              {{ state.enabled ? 'Configured' : 'Not configured' }}
            </span>
          </dd>
        </div>
        <div>
          <dt>Recovery address</dt>
          <dd>{{ state.email || 'Not set' }}</dd>
        </div>
      </dl>
      <p
        v-if="!state.enabled"
        class="muted"
      >
        Email recovery will be available after the mail service is configured during deployment.
      </p>
      <p
        v-if="!state.email"
        class="muted"
      >
        Ask the server administrator to bind your recovery email.
      </p>
      <button
        class="button-secondary"
        :disabled="!state.enabled || !state.email || busy"
        @click="testMail"
      >
        <Mail :size="16" />
        {{ busy ? 'Sending…' : 'Send test email' }}
      </button>
    </template>
    <p
      v-else-if="!error"
      class="muted"
    >
      Loading email status…
    </p>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
  </section>
</template>
