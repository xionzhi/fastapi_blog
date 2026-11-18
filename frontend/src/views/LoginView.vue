<script setup lang="ts">
import { ArrowRight, PenLine } from 'lucide-vue-next'
import { useSignIn } from '../composables/useSignIn'
import WorkspaceAuthCard from '../components/WorkspaceAuthCard.vue'
const { username, password, busy, error, recoveryEnabled, login } = useSignIn()
</script>
<template>
  <WorkspaceAuthCard
    title="Sign in"
    back-to="/"
    back-label="Back to blog"
  >
    <template #icon><PenLine :size="24" /></template>
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
  </WorkspaceAuthCard>
</template>
