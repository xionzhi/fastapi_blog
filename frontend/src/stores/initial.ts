import type { Page, PostDetail, PostSummary, Site } from '../types'

interface InitialDocument {
  site?: Site
  path?: string
  posts?: Page<PostSummary>
  post?: PostDetail
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

function matchesPath(path: string): boolean {
  const source = initialDocument.path
  if (source === undefined) return false
  try {
    return decodeURI(path).replace(/\/+$/, '') === decodeURI(source).replace(/\/+$/, '')
  } catch {
    return false
  }
}

export function takeInitialPosts(path: string): Page<PostSummary> | undefined {
  if (!matchesPath(path)) return
  const posts = initialDocument.posts
  initialDocument.posts = undefined
  return posts
}

export function takeInitialPost(path: string): PostDetail | undefined {
  if (!matchesPath(path)) return
  const post = initialDocument.post
  initialDocument.post = undefined
  return post
}
