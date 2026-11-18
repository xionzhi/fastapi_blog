import { api } from './request'
import type { Tag } from '../types'

export interface TagInput {
  name: string
  slug: string
  description: string
}

export const getPublicTags = (signal?: AbortSignal): Promise<Tag[]> => api('/tags', { signal })
export const getAdminTags = (signal?: AbortSignal): Promise<Tag[]> =>
  api('/admin/tags', { signal, cache: 'no-store' })
export const saveTag = (payload: TagInput, id?: string): Promise<Tag> =>
  api(id ? `/admin/tags/${id}` : '/admin/tags', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
export const deleteTag = (id: string): Promise<void> =>
  api(`/admin/tags/${id}`, { method: 'DELETE' })
