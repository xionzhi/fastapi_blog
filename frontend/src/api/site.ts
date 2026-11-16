import { api } from './request'
import type { Site } from '../types'

export const getSite = (): Promise<Site> => api('/site')
export const getAdminSite = (): Promise<Site> => api('/admin/site')
export const updateSite = (payload: Site): Promise<Site> =>
  api('/admin/site', { method: 'PUT', body: JSON.stringify(payload) })
