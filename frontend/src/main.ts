import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { loadSite } from './stores/site'
import { configureHttpClient } from './api/request'
import { clearSession, session } from './stores/session'
import { notify } from './stores/notifications'
import { errorMessage } from './utils/format'
import './style.css'
import './auth.css'

configureHttpClient({ csrfToken: () => session.csrf, onUnauthorized: clearSession })

async function bootstrap(): Promise<void> {
  try {
    await loadSite()
  } catch (error) {
    notify(errorMessage(error))
  }
  createApp(App).use(router).mount('#app')
}

void bootstrap()
