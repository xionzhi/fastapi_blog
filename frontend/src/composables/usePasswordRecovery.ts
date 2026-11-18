import { getRecoveryStatus, requestReset } from '../api/auth'
import { onScopeDispose, ref } from 'vue'
import { errorMessage } from '../utils/format'

export function usePasswordRecovery() {
  const identifier = ref('')
  const enabled = ref(false)
  const checking = ref(true)
  const busy = ref(false)
  const message = ref('')
  const error = ref('')
  let disposed = false
  onScopeDispose(() => {
    disposed = true
  })
  getRecoveryStatus()
    .then((r) => (enabled.value = r.enabled))
    .catch((e) => (error.value = errorMessage(e)))
    .finally(() => (checking.value = false))
  async function submit() {
    if (busy.value || checking.value || !enabled.value || message.value) return
    busy.value = true
    error.value = ''
    try {
      const result = await requestReset(identifier.value)
      if (!disposed) message.value = result.message
    } catch (e) {
      if (!disposed) error.value = errorMessage(e)
    } finally {
      if (!disposed) busy.value = false
    }
  }
  return { identifier, enabled, checking, busy, message, error, submit }
}
