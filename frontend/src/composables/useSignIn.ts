import { signIn, getRecoveryStatus } from '../api/auth'
import { applySession } from '../stores/session'
import { onScopeDispose, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '../utils/format'

export function useSignIn() {
  const username = ref('')
  const password = ref('')
  const busy = ref(false)
  const error = ref('')
  const recoveryEnabled = ref(false)
  let disposed = false
  onScopeDispose(() => {
    disposed = true
    password.value = ''
  })
  getRecoveryStatus()
    .then((r) => (recoveryEnabled.value = r.enabled))
    .catch(() => {})
  const route = useRoute()
  const router = useRouter()
  async function login() {
    if (busy.value) return
    busy.value = true
    error.value = ''
    try {
      const user = await signIn({ username: username.value, password: password.value })
      if (disposed) return
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
      if (!disposed) error.value = errorMessage(e)
    } finally {
      if (!disposed) busy.value = false
    }
  }
  return { username, password, busy, error, recoveryEnabled, login }
}
