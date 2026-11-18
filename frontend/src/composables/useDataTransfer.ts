import { computed, onScopeDispose, ref } from 'vue'
import { useWorkspaceExitGuard } from './useWorkspaceExitGuard'
import {
  exportData,
  importData,
  MAX_JSON_BYTES,
  previewData,
  type ImportPreview,
  type ImportResult,
} from '../api/transfer'
import { loadSite } from '../stores/site'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'

export function useDataTransfer() {
  const preview = ref<ImportPreview>()
  const result = ref<ImportResult>()
  const filename = ref('')
  const error = ref('')
  const activity = ref<'' | 'export' | 'preview' | 'import'>('')
  const includeSettings = ref(false)
  const allowMissingFiles = ref(false)
  const confirmed = ref(false)
  let content = ''
  let disposed = false
  let request: AbortController | undefined
  const busy = computed(() => Boolean(activity.value))
  const canImport = computed(
    () =>
      !busy.value &&
      preview.value?.can_import &&
      confirmed.value &&
      (!preview.value.missing_files.length || allowMissingFiles.value),
  )

  async function download(): Promise<void> {
    if (busy.value) return
    activity.value = 'export'
    error.value = ''
    request = new AbortController()
    try {
      const blob = await exportData(request.signal)
      if (disposed) return
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `xionzhi-blog-${new Date().toISOString().slice(0, 10)}.json`
      document.body.append(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (cause) {
      if (!disposed) error.value = errorMessage(cause)
    } finally {
      if (!disposed) activity.value = ''
    }
  }

  async function selectFile(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file || busy.value) return
    preview.value = undefined
    result.value = undefined
    confirmed.value = false
    allowMissingFiles.value = false
    error.value = ''
    filename.value = file.name
    content = ''
    activity.value = 'preview'
    request = new AbortController()
    try {
      if (file.size > MAX_JSON_BYTES) throw new Error('Choose a JSON file up to 16 MB.')
      content = await file.text()
      if (disposed) return
      const checked = await previewData(content, request.signal)
      if (!disposed) preview.value = checked
    } catch (cause) {
      if (!disposed) error.value = errorMessage(cause)
    } finally {
      input.value = ''
      if (!disposed) activity.value = ''
    }
  }

  async function apply(): Promise<void> {
    if (!canImport.value || !preview.value) return
    activity.value = 'import'
    error.value = ''
    try {
      result.value = await importData(
        content,
        preview.value.sha256,
        includeSettings.value,
        allowMissingFiles.value,
      )
      preview.value = undefined
      confirmed.value = false
      content = ''
      if (includeSettings.value) {
        try {
          await loadSite(true)
        } catch {
          notify('Import completed. Reload to refresh site settings.')
        }
      }
    } catch (cause) {
      if (!disposed) error.value = errorMessage(cause)
    } finally {
      if (!disposed) activity.value = ''
    }
  }

  useWorkspaceExitGuard(() => {
    if (activity.value !== 'import') return true
    notify('Import is running. Wait for it to finish before leaving this page.')
    return false
  })
  onScopeDispose(() => {
    disposed = true
    request?.abort()
  })
  return {
    preview,
    result,
    filename,
    error,
    activity,
    busy,
    canImport,
    includeSettings,
    allowMissingFiles,
    confirmed,
    download,
    selectFile,
    apply,
  }
}
