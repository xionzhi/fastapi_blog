import { createRouter, createWebHistory } from 'vue-router'
import { checkSession } from './stores/session'
import { site } from './stores/site'
import { notify } from './stores/notifications'
import { errorMessage } from './utils/format'

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
    { path: '/:slug', component: () => import('./views/PostView.vue') },
    { path: '/:pathMatch(.*)*', component: () => import('./views/NotFound.vue') },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path.startsWith('/workspace')) return { top: 0 }
    if (to.hash) return { el: decodeURIComponent(to.hash), top: 30, behavior: 'smooth' }
    if (to.path !== from.path && to.params.page) return { el: '#content', top: 20 }
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
router.afterEach((to) => {
  if (to.path.startsWith('/workspace')) {
    const title = to.path.includes('/analytics')
      ? 'Analytics'
      : to.path.includes('/settings')
        ? 'Settings'
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
    document.title = `${title} · ${site.value.title}`
  }
})
