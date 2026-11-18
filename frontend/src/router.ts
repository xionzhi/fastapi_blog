import { createRouter, createWebHistory } from 'vue-router'
import { checkSession } from './stores/session'
import { site } from './stores/site'
import { notify } from './stores/notifications'
import { errorMessage } from './utils/format'
import { updatePageMetadata } from './utils/metadata'

const COLLECTION_PATH = /^\/(?:page\/\d+\/?|(?:tag|author)\/[^/]+(?:\/page\/\d+)?\/?)?$/

function waitForAnchor(id: string, path: string): Promise<HTMLElement | null> {
  const ready = (): HTMLElement | null => {
    const element = document.getElementById(id)
    return element && !element.closest('[aria-busy="true"]') ? element : null
  }
  const present = ready()
  if (present) return Promise.resolve(present)
  return new Promise((resolve) => {
    const finish = (element: HTMLElement | null): void => {
      observer.disconnect()
      clearTimeout(timer)
      resolve(element)
    }
    const observer = new MutationObserver(() => {
      if (window.location.pathname !== path) finish(null)
      else if (ready()) finish(ready())
    })
    const timer = setTimeout(() => finish(null), 20000)
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-busy'],
    })
  })
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/workspace/login', component: () => import('./views/LoginView.vue') },
    {
      path: '/workspace/forgot-password',
      component: () => import('./views/ForgotPasswordView.vue'),
    },
    { path: '/workspace/reset-password', component: () => import('./views/ResetPasswordView.vue') },
    {
      path: '/workspace',
      component: () => import('./views/AdminLayout.vue'),
      meta: { admin: true },
      children: [
        { path: '', redirect: '/workspace/posts' },
        { path: 'posts', component: () => import('./views/AdminPosts.vue') },
        { path: 'posts/new', component: () => import('./views/EditorView.vue') },
        { path: 'posts/:id', component: () => import('./views/EditorView.vue') },
        { path: 'tags', component: () => import('./views/AdminTags.vue') },
        { path: 'images', component: () => import('./views/AdminMedia.vue') },
        { path: 'analytics', component: () => import('./views/AdminAnalytics.vue') },
        { path: 'settings', component: () => import('./views/AdminSettings.vue') },
      ],
    },
    { path: '/', component: () => import('./views/HomeView.vue') },
    { path: '/page/:page(\\d+)', component: () => import('./views/HomeView.vue') },
    { path: '/tag/:tag/page/:page(\\d+)', component: () => import('./views/HomeView.vue') },
    { path: '/tag/:tag', component: () => import('./views/HomeView.vue') },
    { path: '/author/:author/page/:page(\\d+)', component: () => import('./views/HomeView.vue') },
    { path: '/author/:author', component: () => import('./views/HomeView.vue') },
    { path: '/archive', component: () => import('./views/ArchiveView.vue') },
    { path: '/tags', component: () => import('./views/TagsView.vue') },
    {
      path: '/preview/:id([a-f0-9]{32})',
      name: 'draft-preview',
      sensitive: true,
      component: () => import('./views/PostView.vue'),
    },
    { path: '/:slug', component: () => import('./views/PostView.vue') },
    { path: '/:pathMatch(.*)*', component: () => import('./views/NotFound.vue') },
  ],
  async scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path === from.path && !to.hash) return false
    if (to.path.startsWith('/workspace')) return { top: 0 }
    if (to.hash) {
      let id: string
      try {
        id = decodeURIComponent(to.hash.slice(1))
      } catch {
        return false
      }
      const element = await waitForAnchor(id, to.path)
      return element
        ? {
            el: element,
            top: 30,
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
              ? 'auto'
              : 'smooth',
          }
        : false
    }
    if (
      to.path !== from.path &&
      COLLECTION_PATH.test(to.path) &&
      COLLECTION_PATH.test(from.path) &&
      to.params.tag === from.params.tag &&
      to.params.author === from.params.author
    )
      return { el: '#content', top: 20 }
    return { top: 0 }
  },
})
router.beforeEach(async (to) => {
  if (!to.meta.admin) return
  try {
    if (await checkSession()) return
  } catch (error) {
    notify(errorMessage(error))
  }
  return { path: '/workspace/login', query: { next: to.fullPath } }
})
router.onError(() => {
  notify('This page could not be loaded. Please check your connection and reload.')
})
router.afterEach((to, _from, failure) => {
  if (failure) return
  updatePageMetadata(to.path, site.value)
  if (to.path.startsWith('/workspace')) {
    const title = to.path.includes('/analytics')
      ? 'Analytics'
      : to.path.includes('/settings')
        ? 'Settings'
        : to.path.includes('/images')
          ? 'Images'
          : to.path.includes('/tags')
            ? 'Tags'
            : to.path.includes('/login')
              ? 'Sign in'
              : to.path.includes('/forgot-password')
                ? 'Forgot password'
                : to.path.includes('/reset-password')
                  ? 'Reset password'
                  : to.params.id || to.path.endsWith('/new')
                    ? 'Edit post'
                    : 'Posts'
    updatePageMetadata(to.path, site.value, { title: `${title} · ${site.value.title}` })
  }
})
