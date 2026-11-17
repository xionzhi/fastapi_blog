import type { LibraryImage } from '../api/media'

export function imageMarkup(url: string, alt: string, format: 'markdown' | 'html'): string {
  if (format === 'markdown') return `![${alt.replace(/[\\[\]]/g, '\\$&')}](${url})`
  const entities: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }
  const escape = (text: string): string =>
    text.replace(/[&<>"']/g, (character) => entities[character] ?? character)
  return `<img src="${escape(url)}" alt="${escape(alt)}">`
}

export const imageAlt = (image: LibraryImage): string => image.name.replace(/\.[^.]+$/, '')

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
