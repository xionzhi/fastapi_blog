import { api, queryString } from './request'
import type {
  Page,
  PostSummary,
  PostDetail,
  PostRedirect,
  AdminPostSummary,
  AdminPostDetail,
} from '../types'

export interface PostQuery {
  page?: number
  limit?: number
  q?: string
  tag?: string
  author?: string
  status?: string
  type?: string
}
export interface PostInput {
  title: string
  slug: string
  body: string
  format: 'markdown' | 'html'
  excerpt: string
  status: 'draft' | 'published'
  type: 'post' | 'page'
  feature_image: string
  author: string
  author_slug: string
  tags: string[]
  published_at: string | null
  version?: number
}
export interface PostStatistics {
  total: number
  draft: number
  published: number
  tags: number
}

export const getPosts = (query: PostQuery = {}, signal?: AbortSignal): Promise<Page<PostSummary>> =>
  api(`/posts?${queryString(query)}`, { signal })
export const getPost = (slug: string): Promise<PostDetail | PostRedirect> =>
  api(`/posts/${encodeURIComponent(slug)}`)
export const getAdminPosts = (query: PostQuery = {}): Promise<Page<AdminPostSummary>> =>
  api(`/admin/posts?${queryString(query)}`)
export const getAdminPost = (id: string): Promise<AdminPostDetail> => api(`/admin/posts/${id}`)
export const getPostStatistics = (): Promise<PostStatistics> => api('/admin/stats')
export const savePost = (payload: PostInput, id?: string): Promise<AdminPostDetail> =>
  api(id ? `/admin/posts/${id}` : '/admin/posts', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
export const deletePost = (id: string): Promise<void> =>
  api(`/admin/posts/${id}`, { method: 'DELETE' })
export const previewPost = (
  body: string,
  format: PostInput['format'],
  signal?: AbortSignal,
): Promise<{ html: string }> =>
  api('/admin/preview', { method: 'POST', body: JSON.stringify({ body, format }), signal })
