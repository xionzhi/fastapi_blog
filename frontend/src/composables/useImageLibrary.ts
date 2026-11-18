import { computed, nextTick, onScopeDispose, ref, watch } from 'vue'
import { useWorkspaceExitGuard } from './useWorkspaceExitGuard'
import { deleteImage, getImages, moveImage, uploadImage, type LibraryImage } from '../api/media'
import { ApiError } from '../api/request'
import { notify } from '../stores/notifications'
import { loadSite } from '../stores/site'
import { errorMessage } from '../utils/format'
import { useAsyncResource } from './useAsyncResource'
import { useDebouncedTask } from './useDebouncedTask'

export function useImageLibrary() {
  const search = ref('')
  const query = ref('')
  const page = ref(1)
  const busy = ref(false)
  const operationError = ref('')
  const selected = ref<LibraryImage>()
  const task = useDebouncedTask(300)
  let disposed = false
  const {
    data,
    loading,
    error: loadError,
    reload,
  } = useAsyncResource(
    () => [query.value, page.value],
    (signal) => getImages(query.value, page.value, signal),
  )
  const error = computed(() => operationError.value || loadError.value)
  watch(search, () => {
    selected.value = undefined
    task.schedule(async () => {
      page.value = 1
      query.value = search.value.trim()
    })
  })
  watch(data, (result) => {
    if (!result) return
    if (page.value > result.pages) page.value = result.pages
    if (selected.value)
      selected.value = result.items.find((item) => item.path === selected.value?.path)
  })
  onScopeDispose(() => {
    disposed = true
  })
  useWorkspaceExitGuard(() => {
    if (!busy.value) return true
    notify('Wait for the image operation to finish before leaving.')
    return false
  })

  async function run(action: () => Promise<void>): Promise<boolean> {
    if (busy.value || loading.value) return false
    busy.value = true
    operationError.value = ''
    const previousQuery = query.value
    const previousPage = page.value
    try {
      await action()
      if (!disposed) {
        if (query.value === previousQuery && page.value === previousPage) await reload()
        else await nextTick() // The resource watcher already reloads changed criteria.
      }
      return !disposed
    } catch (cause) {
      if (!disposed) {
        operationError.value = errorMessage(cause)
        if (cause instanceof ApiError && [404, 409].includes(cause.status)) await reload()
      }
      return false
    } finally {
      if (!disposed) busy.value = false
    }
  }

  async function upload(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    await run(async () => {
      if (file.size > 20 * 1024 * 1024) throw new Error('Images must not exceed 20 MB.')
      await uploadImage(file)
      task.cancel()
      search.value = ''
      query.value = ''
      page.value = 1
      notify('Image uploaded')
    })
    input.value = ''
  }

  async function move(image: LibraryImage, path: string): Promise<void> {
    await run(async () => {
      const result = await moveImage(image, path)
      selected.value = result.image
      notify(
        result.source_retained
          ? 'Image moved and references updated. The original file was retained; refresh to review it.'
          : 'Image moved. Saved references updated.',
      )
      if (image.usages.some((usage) => usage.url === '/workspace/settings')) {
        void loadSite(true).catch(() => {})
      }
    })
  }

  async function remove(image: LibraryImage): Promise<boolean> {
    return run(async () => {
      await deleteImage(image)
      selected.value = undefined
      notify('Image deleted')
    })
  }

  return { search, page, data, loading, busy, error, selected, reload, upload, move, remove }
}
