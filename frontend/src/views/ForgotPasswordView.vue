<script setup lang="ts">
import { ArrowRight, Mail, CheckCircle } from 'lucide-vue-next'
import { usePasswordRecovery } from '../composables/usePasswordRecovery'
import WorkspaceAuthCard from '../components/WorkspaceAuthCard.vue'
const { identifier, enabled, checking, busy, message, error, submit } = usePasswordRecovery()
</script>
<template>
  <WorkspaceAuthCard
    :title="message ? 'Check your inbox' : 'Forgot your password?'"
    recovery
  >
    <template #icon>
      <CheckCircle
        v-if="message"
        :size="24"
      />
      <Mail
        v-else
        :size="24"
      />
    </template>
    <p
      v-if="checking"
      class="muted"
      role="status"
    >
      Checking email availability…
    </p>
    <template v-else-if="message">
      <p
        class="muted"
        role="status"
      >
        {{ message }}
      </p>
      <RouterLink
        class="button-secondary"
        to="/workspace/login"
      >
        Back to sign in
      </RouterLink>
    </template>
    <template v-else-if="!enabled">
      <p class="muted">
        Email recovery has not been enabled. Contact the blog administrator for help.
      </p>
      <RouterLink
        class="button-secondary"
        to="/workspace/login"
      >
        Back to sign in
      </RouterLink>
    </template>
    <form
      v-else
      @submit.prevent="submit"
    >
      <p class="muted">
        Enter your administrator username or recovery email. We will send a link that expires in 15
        minutes.
      </p>
      <label>
        Username or email
        <input
          v-model="identifier"
          autocomplete="username"
          required
          autofocus
          maxlength="254"
        />
      </label>
      <button
        class="button-primary"
        :disabled="busy"
      >
        {{ busy ? 'Requesting…' : 'Send reset link' }}
        <ArrowRight :size="17" />
      </button>
    </form>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
  </WorkspaceAuthCard>
</template>
