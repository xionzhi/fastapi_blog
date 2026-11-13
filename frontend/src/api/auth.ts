import { api } from './request'

export interface SessionResponse {
  username: string
  csrf_token: string
}
export interface MessageResponse {
  message: string
}
export interface LoginPayload {
  username: string
  password: string
}

export const getSession = (): Promise<SessionResponse> => api('/admin/me')
export const signIn = (payload: LoginPayload): Promise<SessionResponse> =>
  api('/admin/login', { method: 'POST', body: JSON.stringify(payload) })
export const signOut = (): Promise<{ ok: boolean }> => api('/admin/logout', { method: 'POST' })
export const getRecoveryStatus = (): Promise<{ enabled: boolean }> => api('/auth/recovery')
export const requestReset = (identifier: string): Promise<MessageResponse> =>
  api('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ identifier }) })
export const checkResetToken = (token: string): Promise<{ valid: boolean }> =>
  api('/auth/reset-password/check', { method: 'POST', body: JSON.stringify({ token }) })
export const resetPassword = (token: string, password: string): Promise<MessageResponse> =>
  api('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) })
