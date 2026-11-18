import { onScopeDispose } from 'vue'
import { onBeforeRouteLeave, type RouteLocationNormalized } from 'vue-router'

type ExitGuard = (to?: RouteLocationNormalized) => boolean
const guards = new Set<ExitGuard>()
let exiting = false
let approved = false

/** Apply the same pending-operation and unsaved-edit checks before navigation or sign-out. */
export function useWorkspaceExitGuard(guard: ExitGuard): void {
  guards.add(guard)
  onBeforeRouteLeave((to) => approved || guard(to))
  onScopeDispose(() => guards.delete(guard))
}

export async function exitWorkspace(
  signOut: () => Promise<void>,
  navigate: () => Promise<unknown>,
): Promise<boolean> {
  if (exiting) return false
  exiting = true
  try {
    for (const guard of guards) if (!guard()) return false
    await signOut()
    approved = true
    await navigate()
    return true
  } finally {
    approved = false
    exiting = false
  }
}
