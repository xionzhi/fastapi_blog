import type { Site } from '../types'

export interface PageMetadata {
  title?: string
  description?: string
  image?: string
  type?: 'article' | 'website'
}

const siteOrigin = new URL(
  document.querySelector<HTMLLinkElement>('link[rel="canonical"]')?.href || location.origin,
).origin

/** Replace document metadata together so client navigation cannot retain the previous page. */
export function updatePageMetadata(path: string, site: Site, details: PageMetadata = {}): void {
  const title = details.title || site.title
  const description = details.description ?? site.description
  const image = details.image || site.cover
  const canonical = new URL(
    siteOrigin + '/' + path.replace(/^\/+|\/+$/g, '') + (path === '/' ? '' : '/'),
  ).href
  document.title = title
  document.head
    .querySelectorAll(
      'meta[name="description"],link[rel="canonical"],meta[property^="og:"],meta[name="robots"]',
    )
    .forEach((node) => node.remove())
  const link = document.createElement('link')
  link.rel = 'canonical'
  link.href = canonical
  document.head.append(link)
  const values = {
    title,
    description,
    url: canonical,
    image: image ? new URL(image, siteOrigin).href : '',
    type: details.type || 'website',
  }
  const meta = (key: 'name' | 'property', name: string, content: string): void => {
    const element = document.createElement('meta')
    element.setAttribute(key, name)
    element.content = content
    document.head.append(element)
  }
  meta('name', 'description', description)
  for (const [key, value] of Object.entries(values)) meta('property', `og:${key}`, value)
  if (/^\/workspace(?:\/|$)/.test(path)) meta('name', 'robots', 'noindex,nofollow')
}
