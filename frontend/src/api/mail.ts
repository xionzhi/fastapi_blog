import { api } from './request'
import type { MessageResponse } from './auth'

export interface MailStatus {
  enabled: boolean
  email: string
}
export const getMailStatus = (): Promise<MailStatus> => api('/admin/mail')
export const sendTestEmail = (): Promise<MessageResponse> =>
  api('/admin/mail/test', { method: 'POST' })
