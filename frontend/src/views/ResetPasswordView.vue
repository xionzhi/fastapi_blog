<script setup lang="ts">
import { KeyRound, CheckCircle } from 'lucide-vue-next'
import { usePasswordReset } from '../composables/usePasswordReset'
import WorkspaceAuthCard from '../components/WorkspaceAuthCard.vue'
const { valid, checking, password, confirmation, busy, error, message, submit } = usePasswordReset()
</script>
<template>
  <WorkspaceAuthCard
    :title="message ? 'Password updated' : 'Set a new password'"
    recovery
  >
    <template #icon>
      <CheckCircle
        v-if="message"
        :size="24"
      />
      <KeyRound
        v-else
        :size="24"
      />
    </template>
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
  </WorkspaceAuthCard>
</template>
