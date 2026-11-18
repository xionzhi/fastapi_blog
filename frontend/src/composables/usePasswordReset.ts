import { checkResetToken, resetPassword } from '../api/auth'
import { clearSession } from '../stores/session'
import { onScopeDispose, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '../utils/format'

export function usePasswordReset() {
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
  let disposed = false
  onScopeDispose(() => {
    disposed = true
    password.value = ''
    confirmation.value = ''
  })
  // Remove the one-time credential from visible history as soon as it is captured.
  if (route.hash) router.replace({ path: '/workspace/reset-password', hash: '' })
  async function check() {
    try {
      await checkResetToken(token)
      if (!disposed) valid.value = true
    } catch (e) {
      if (!disposed) error.value = errorMessage(e)
    } finally {
      if (!disposed) checking.value = false
    }
  }
  if (token) check()
  else {
    checking.value = false
    error.value = 'This reset link is missing or invalid. Please request a new one.'
  }
  async function submit() {
    if (busy.value || checking.value || !valid.value || message.value) return
    if (password.value !== confirmation.value) {
      error.value = 'Passwords do not match.'
      return
    }
    busy.value = true
    error.value = ''
    try {
      const result = await resetPassword(token, password.value)
      if (disposed) return
      message.value = result.message
      password.value = ''
      confirmation.value = ''
      clearSession()
    } catch (e) {
      if (!disposed) error.value = errorMessage(e)
    } finally {
      if (!disposed) busy.value = false
    }
  }
  return { valid, checking, password, confirmation, busy, error, message, submit }
}
