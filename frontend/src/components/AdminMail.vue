<script setup lang="ts">
import { Mail, Pencil, Save } from 'lucide-vue-next'
import { useAdminMail } from '../composables/useAdminMail'

const {
  state,
  error,
  busy,
  editing,
  email,
  password,
  emailInput,
  activity,
  canSave,
  edit,
  cancel,
  save,
  testMail,
  reload,
} = useAdminMail()
</script>
<template>
  <section class="content-panel settings-section mail-section">
    <h2>Administrator email</h2>
    <p class="muted">
      Password reset links and account security notifications are sent to your administrator email.
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
          <dt>Administrator email</dt>
          <dd class="mail-address">
            <span>{{ state.email || 'Not set' }}</span>
            <button
              v-if="!editing"
              type="button"
              class="button-secondary"
              :disabled="busy"
              @click="edit"
            >
              <Pencil :size="14" />
              {{ state.email ? 'Change email' : 'Set email' }}
            </button>
          </dd>
        </div>
      </dl>
      <form
        v-if="editing"
        class="recovery-email-form"
        @submit.prevent="save"
      >
        <h3>{{ state.email ? 'Change administrator email' : 'Set administrator email' }}</h3>
        <p class="muted">
          Enter your blog login password to confirm this change. Changing your email signs out other
          sessions and invalidates existing password reset links.
        </p>
        <label>
          Administrator email address
          <input
            ref="emailInput"
            v-model="email"
            type="email"
            autocomplete="email"
            maxlength="254"
            required
            :disabled="busy"
          />
        </label>
        <label>
          Current login password
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            maxlength="1024"
            required
            :disabled="busy"
          />
        </label>
        <div class="mail-actions">
          <button
            type="submit"
            class="button-primary"
            :disabled="!canSave"
          >
            <Save :size="16" />
            {{ activity === 'save' ? 'Saving…' : 'Save email' }}
          </button>
          <button
            type="button"
            class="button-secondary"
            :disabled="busy"
            @click="cancel"
          >
            Cancel
          </button>
        </div>
      </form>
      <p
        v-if="!state.enabled"
        class="muted"
      >
        Email delivery is not configured. You can still save your administrator email.
      </p>
      <p
        v-else
        class="muted"
      >
        {{
          state.email
            ? 'Send a test email to check delivery to this address.'
            : 'Set your administrator email to enable password recovery.'
        }}
      </p>
      <button
        type="button"
        class="button-secondary"
        :disabled="!state.enabled || !state.email || busy || editing"
        @click="testMail"
      >
        <Mail :size="16" />
        {{ activity === 'test' ? 'Sending…' : 'Send test email' }}
      </button>
    </template>
    <p
      v-else-if="!error"
      class="muted"
    >
      Loading email status…
    </p>
    <button
      v-if="!state && error"
      type="button"
      class="button-secondary"
      :disabled="busy"
      @click="reload"
    >
      Reload email status
    </button>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
  </section>
</template>
