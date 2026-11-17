import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { loadSite } from './stores/site'
import { configureHttpClient } from './api/request'
import { clearSession, session } from './stores/session'
import { notify } from './stores/notifications'
import { errorMessage } from './utils/format'
import './styles/casper.css'
import './styles/fonts.css'
import './style.css'
import './auth.css'
import { initialDocument } from './stores/initial'

configureHttpClient({ csrfToken: () => session.csrf, onUnauthorized: clearSession })

async function bootstrap(): Promise<void> {
  try {
    if (!initialDocument.site) await loadSite()
  } catch (error) {
    notify(errorMessage(error))
  }
  const app = createApp(App).use(router)
  await router.isReady()
  app.mount('#app')
}

void bootstrap()
