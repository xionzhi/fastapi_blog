import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { signOut } from '../api/auth'
import { clearSession } from '../stores/session'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'
import { exitWorkspace } from './useWorkspaceExitGuard'

export function useSignOut() {
  const router = useRouter()
  const busy = ref(false)
  async function logout(): Promise<void> {
    if (busy.value) return
    busy.value = true
    try {
      await exitWorkspace(
        async () => {
          await signOut()
          clearSession()
        },
        () => router.push('/workspace/login'),
      )
    } catch (cause) {
      notify(errorMessage(cause))
    } finally {
      busy.value = false
    }
  }
  return { busy, logout }
}
