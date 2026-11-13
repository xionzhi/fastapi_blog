import { api } from './request'

export async function uploadImage(file: File): Promise<{ url: string }> {
  const body = new FormData()
  body.append('file', file)
  return api('/admin/images', { method: 'POST', body })
}
