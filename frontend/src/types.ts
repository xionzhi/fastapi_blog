export interface Tag {
  id: string
  name: string
  slug: string
  description?: string
  count?: number
}
export interface PostSummary {
  id: string
  title: string
  slug: string
  excerpt: string
  status: 'draft' | 'published'
  type: 'post' | 'page'
  feature_image: string
  author: string
  author_slug: string
  tags: Tag[]
  published_at: string | null
  created_at: string
  updated_at: string
  version: number
  reading_time: number
}
export interface Page<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
}
export interface Site {
  images?: Record<
    string,
    { src: string; width: number; height: number; srcset: string; sizes: string }
  >
  title: string
  description: string
  cover: string
  logo: string
  author: string
  author_image: string
  author_bio: string
  navigation: { label: string; url: string }[]
  posts_per_page: number
  stats?: { posts: number; tags: number }
}

export interface PostDetail extends PostSummary {
  html: string
  related: PostSummary[]
}

export interface AdminPostSummary extends PostSummary {
  format: 'markdown' | 'html'
}

export interface AdminPostDetail extends AdminPostSummary {
  body: string
  html: string
}

export interface PostRedirect {
  redirect: string
}
