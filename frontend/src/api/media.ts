import { api } from './request'
import type { Page } from '../types'

export interface LibraryImage {
  path: string
  name: string
  url: string
  thumbnail: string
  size: number
  modified_at: string
  revision: string
  usages: { title: string; url: string }[]
}

export const getImages = (
  q: string,
  page: number,
  signal?: AbortSignal,
): Promise<Page<LibraryImage>> =>
  api(`/admin/images?${new URLSearchParams({ q, page: String(page), limit: '24' })}`, { signal })

export const moveImage = (
  image: LibraryImage,
  newPath: string,
): Promise<{ image: LibraryImage; source_retained: boolean }> =>
  api('/admin/images', {
    method: 'PUT',
    body: JSON.stringify({ path: image.path, revision: image.revision, new_path: newPath }),
  })

export const deleteImage = (image: LibraryImage): Promise<void> =>
  api('/admin/images', {
    method: 'DELETE',
    body: JSON.stringify({ path: image.path, revision: image.revision }),
  })

export async function uploadImage(file: File): Promise<{ url: string }> {
  const body = new FormData()
  body.append('file', file)
  return api('/admin/images', { method: 'POST', body })
}
