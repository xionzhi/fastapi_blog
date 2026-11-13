/** Shared session state. The HTTP client does not import or mutate this module. */
import { reactive } from 'vue'
import { getSession, type SessionResponse } from '../api/auth'
import { ApiError } from '../api/request'

export const session = reactive({ username: '', csrf: '' })
let pendingCheck: Promise<boolean> | undefined

export function applySession(user: SessionResponse): void {
  session.username = user.username
  session.csrf = user.csrf_token
}

export function clearSession(): void {
  session.username = ''
  session.csrf = ''
}

async function fetchSession(): Promise<boolean> {
  try {
    applySession(await getSession())
    return true
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error
    clearSession()
    return false
  }
}

export async function checkSession(): Promise<boolean> {
  pendingCheck ??= fetchSession().finally(() => {
    pendingCheck = undefined
  })
  return pendingCheck
}
