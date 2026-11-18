import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { deleteTag, getAdminTags, saveTag, type TagInput } from '../api/tags'
import { notify } from '../stores/notifications'
import { errorMessage } from '../utils/format'
import type { Tag } from '../types'

export function useTagManagement() {
  const tags = ref<Tag[]>([])
  const loading = ref(false)
  const editing = ref(false)
  const id = ref('')
  const form = ref<TagInput>({ name: '', slug: '', description: '' })
  const deleteTarget = shallowRef<Tag>()
  const pageError = ref('')
  const formError = ref('')
  const deleteError = ref('')
  const activity = ref<'' | 'save' | 'delete'>('')
  const busy = computed(() => activity.value !== '')
  let request: AbortController | undefined
  let disposed = false

  function cancelLoad(): void {
    request?.abort()
    request = undefined
    loading.value = false
  }

  async function load(): Promise<void> {
    if (busy.value || disposed) return
    cancelLoad()
    const current = new AbortController()
    request = current
    loading.value = true
    pageError.value = ''
    try {
      const result = await getAdminTags(current.signal)
      if (!disposed && !current.signal.aborted) tags.value = result
    } catch (cause) {
      if (!disposed && !current.signal.aborted) pageError.value = errorMessage(cause)
    } finally {
      if (request === current) {
        request = undefined
        loading.value = false
      }
    }
  }

  function edit(tag?: Tag): void {
    if (busy.value || editing.value || deleteTarget.value) return
    id.value = tag?.id ?? ''
    form.value = {
      name: tag?.name ?? '',
      slug: tag?.slug ?? '',
      description: tag?.description ?? '',
    }
    formError.value = ''
    editing.value = true
  }

  function closeEditor(): void {
    if (!busy.value) editing.value = false
  }

  async function save(): Promise<void> {
    if (busy.value || !editing.value) return
    cancelLoad()
    activity.value = 'save'
    formError.value = ''
    try {
      const previous = tags.value.find((tag) => tag.id === id.value)
      const saved = await saveTag({ ...form.value }, id.value || undefined)
      if (disposed) return
      const updated = { ...saved, count: saved.count ?? previous?.count ?? 0 }
      tags.value = [...tags.value.filter((tag) => tag.id !== saved.id), updated].sort(
        (a, b) => (b.count ?? 0) - (a.count ?? 0) || a.name.localeCompare(b.name),
      )
      editing.value = false
      pageError.value = ''
      notify('Tag saved')
    } catch (cause) {
      if (!disposed) formError.value = errorMessage(cause)
    } finally {
      activity.value = ''
    }
  }

  function askToDelete(tag: Tag): void {
    if (busy.value || editing.value || deleteTarget.value) return
    deleteError.value = ''
    deleteTarget.value = tag
  }

  function cancelDelete(): void {
    if (busy.value) return
    deleteTarget.value = undefined
    deleteError.value = ''
  }

  async function remove(): Promise<boolean> {
    const target = deleteTarget.value
    if (!target || busy.value) return false
    // A late list response must not restore the row after a successful mutation.
    cancelLoad()
    activity.value = 'delete'
    deleteError.value = ''
    try {
      await deleteTag(target.id)
      if (disposed) return false
      tags.value = tags.value.filter((tag) => tag.id !== target.id)
      deleteTarget.value = undefined
      pageError.value = ''
      notify('Tag deleted')
      return true
    } catch (cause) {
      if (!disposed) deleteError.value = errorMessage(cause)
      return false
    } finally {
      activity.value = ''
    }
  }

  onBeforeRouteLeave(() => {
    if (!busy.value) return true
    notify('Wait for the tag operation to finish before leaving.')
    return false
  })
  onScopeDispose(() => {
    disposed = true
    cancelLoad()
  })
  void load()

  return {
    tags,
    loading,
    editing,
    id,
    form,
    deleteTarget,
    pageError,
    formError,
    deleteError,
    busy,
    load,
    edit,
    closeEditor,
    save,
    askToDelete,
    cancelDelete,
    remove,
  }
}
