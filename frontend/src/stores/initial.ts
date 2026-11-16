import type { Page, PostSummary, Site } from '../types'

interface InitialDocument {
  site?: Site
  path?: string
  posts?: Page<PostSummary>
}

function readDocument(): InitialDocument {
  const value = document.getElementById('initial-document')?.textContent
  if (!value) return {}
  try {
    const parsed: unknown = JSON.parse(value)
    return parsed && typeof parsed === 'object' ? (parsed as InitialDocument) : {}
  } catch {
    return {}
  }
}

export const initialDocument = readDocument()

export function takeInitialPosts(path: string): Page<PostSummary> | undefined {
  const source = initialDocument.path
  if (source === undefined) return
  try {
    if (decodeURI(path).replace(/\/+$/, '') !== decodeURI(source).replace(/\/+$/, '')) return
  } catch {
    return
  }
  const posts = initialDocument.posts
  initialDocument.posts = undefined
  return posts
}
