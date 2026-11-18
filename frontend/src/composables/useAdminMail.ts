import { computed, nextTick, onScopeDispose, ref } from 'vue'
import { useWorkspaceExitGuard } from './useWorkspaceExitGuard'
import { getMailStatus, sendTestEmail, updateRecoveryEmail } from '../api/mail'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'
import { useAsyncResource } from './useAsyncResource'

export function useAdminMail() {
  const {
    data: state,
    error: loadError,
    loading,
    reload,
  } = useAsyncResource(() => true, getMailStatus)
  const editing = ref(false)
  const email = ref('')
  const password = ref('')
  const emailInput = ref<HTMLInputElement>()
  const activity = ref<'' | 'save' | 'test'>('')
  const operationError = ref('')
  const error = computed(() => operationError.value || loadError.value)
  const busy = computed(() => Boolean(activity.value) || loading.value)
  const canSave = computed(
    () =>
      !busy.value &&
      Boolean(password.value && email.value.trim()) &&
      email.value.trim().toLowerCase() !== state.value?.email.toLowerCase(),
  )
  let disposed = false

  async function edit(): Promise<void> {
    if (busy.value || !state.value) return
    email.value = state.value.email
    password.value = ''
    operationError.value = ''
    editing.value = true
    await nextTick()
    if (!disposed) emailInput.value?.focus()
  }

  function cancel(): void {
    if (busy.value) return
    editing.value = false
    password.value = ''
    operationError.value = ''
  }

  async function save(): Promise<void> {
    if (!canSave.value || !state.value) return
    activity.value = 'save'
    operationError.value = ''
    try {
      const updated = await updateRecoveryEmail({
        email: email.value.trim(),
        previous_email: state.value.email,
        current_password: password.value,
      })
      if (disposed) return
      state.value = updated
      editing.value = false
      notify('Recovery email saved')
    } catch (cause) {
      if (!disposed) operationError.value = errorMessage(cause)
    } finally {
      password.value = ''
      if (!disposed) activity.value = ''
    }
  }

  async function testMail(): Promise<void> {
    if (busy.value || editing.value || !state.value?.enabled || !state.value.email) return
    activity.value = 'test'
    operationError.value = ''
    try {
      const result = await sendTestEmail()
      if (!disposed) notify(result.message)
    } catch (cause) {
      if (!disposed) operationError.value = errorMessage(cause)
    } finally {
      if (!disposed) activity.value = ''
    }
  }

  useWorkspaceExitGuard(() => {
    if (!activity.value) return true
    notify('Wait for the email operation to finish before leaving this page.')
    return false
  })
  onScopeDispose(() => {
    disposed = true
    password.value = ''
  })
  return {
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
  }
}
