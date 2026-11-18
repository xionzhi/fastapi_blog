import { computed, onMounted, onScopeDispose, ref } from 'vue'
import { useWorkspaceExitGuard } from './useWorkspaceExitGuard'
import { updateSite } from '../api/site'
import { site } from '../stores/site'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'
import type { Site } from '../types'

export function useSiteSettings() {
  const cloneSite = () => JSON.parse(JSON.stringify(site.value)) as Site
  const form = ref<Site>(cloneSite())
  const baseline = ref(JSON.stringify(form.value))
  const dirty = computed(() => JSON.stringify(form.value) !== baseline.value)
  const busy = ref(false)
  const error = ref('')
  let disposed = false

  function refreshForm(settingsImported: boolean): void {
    if (!settingsImported || disposed) return
    form.value = cloneSite()
    baseline.value = JSON.stringify(form.value)
  }
  async function save(): Promise<void> {
    if (busy.value || disposed) return
    busy.value = true
    error.value = ''
    const submitted = JSON.stringify(form.value)
    try {
      const saved = await updateSite(JSON.parse(submitted) as Site)
      if (disposed) return
      site.value = saved
      // Preserve any newer edits; only the submitted snapshot is now saved.
      if (JSON.stringify(form.value) === submitted) form.value = cloneSite()
      baseline.value = JSON.stringify(saved)
      notify(dirty.value ? 'Settings saved. Newer edits are still unsaved.' : 'Site settings saved')
    } catch (cause) {
      if (!disposed) error.value = errorMessage(cause)
    } finally {
      if (!disposed) busy.value = false
    }
  }
  useWorkspaceExitGuard(() => {
    if (busy.value) {
      notify('Wait for the settings to finish saving before leaving this page.')
      return false
    }
    return !dirty.value || confirm('You have unsaved settings. Leave this page?')
  })
  function beforeUnload(event: BeforeUnloadEvent): void {
    if (!dirty.value && !busy.value) return
    event.preventDefault()
    event.returnValue = ''
  }
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onScopeDispose(() => {
    disposed = true
    window.removeEventListener('beforeunload', beforeUnload)
  })
  return { form, dirty, busy, error, save, refreshForm }
}
