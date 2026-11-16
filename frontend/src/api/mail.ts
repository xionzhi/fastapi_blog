import { api } from './request'
import type { MessageResponse } from './auth'

export interface MailStatus {
  enabled: boolean
  email: string
}
export const getMailStatus = (signal?: AbortSignal): Promise<MailStatus> =>
  api('/admin/mail', { signal })
export const updateRecoveryEmail = (data: {
  email: string
  previous_email: string
  current_password: string
}): Promise<MailStatus> => api('/admin/mail', { method: 'PUT', body: JSON.stringify(data) })
export const sendTestEmail = (): Promise<MessageResponse> =>
  api('/admin/mail/test', { method: 'POST' })
