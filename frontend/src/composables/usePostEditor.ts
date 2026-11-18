import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import {
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
  useRoute,
  useRouter,
  type RouteLocationNormalized,
} from 'vue-router'
import { getAdminPost, previewPost, savePost, setDraftPreview, type PostInput } from '../api/posts'
import { getAdminTags } from '../api/tags'
import type { LibraryImage } from '../api/media'
import { imageMarkup } from '../utils/images'
import { site } from '../stores/site'
import { notify } from '../stores/notifications'
import { errorMessage, slugify } from '../utils/format'
import { useDebouncedTask } from './useDebouncedTask'
import type { Tag } from '../types'

export type EditorDraft = Omit<PostInput, 'tags'>
export type EditorMode = 'write' | 'split' | 'preview'

function emptyDraft(): EditorDraft {
  return {
    title: '',
    slug: '',
    body: '',
    format: 'markdown',
    excerpt: '',
    status: 'draft',
    type: 'post',
    feature_image: '',
    author: site.value.author,
    author_slug: 'xionzhi',
    published_at: null,
    version: undefined,
  }
}

/** Own editing state and side effects. The page renders it without knowing HTTP details. */
export function usePostEditor(textarea: Ref<HTMLTextAreaElement | undefined>) {
  const route = useRoute()
  const router = useRouter()
  const model = ref<EditorDraft>(emptyDraft())
  const id = ref('')
  const tagText = ref('')
  const tags = ref<Tag[]>([])
  const baseline = ref('')
  const mode = ref<EditorMode>('write')
  const html = ref('')
  const loading = ref(true)
  const ready = ref(false)
  const busy = ref(false)
  const libraryOpen = ref(false)
  let selection: [number, number] = [0, 0]
  const error = ref('')
  const previewError = ref('')
  const previewing = ref(false)
  const previewShared = ref(false)
  const automaticSlug = ref(true)
  const previewTask = useDebouncedTask(350)
  let loadSequence = 0

  const snapshot = (): string => JSON.stringify([model.value, tagText.value])
  const dirty = computed(() => Boolean(baseline.value) && snapshot() !== baseline.value)

  async function load(): Promise<void> {
    const sequence = ++loadSequence
    const requestedId = String(route.params.id || '')
    loading.value = true
    ready.value = false
    id.value = ''
    previewShared.value = false
    baseline.value = ''
    model.value = emptyDraft()
    tagText.value = ''
    html.value = ''
    mode.value = 'write'
    libraryOpen.value = false
    error.value = ''
    try {
      const [availableTags, post] = await Promise.all([
        getAdminTags(),
        requestedId ? getAdminPost(requestedId) : Promise.resolve(undefined),
      ])
      if (sequence !== loadSequence) return
      tags.value = availableTags
      automaticSlug.value = !post
      id.value = post?.id ?? ''
      previewShared.value = post?.preview_shared ?? false
      model.value = post
        ? {
            title: post.title,
            slug: post.slug,
            body: post.body,
            format: post.format,
            excerpt: post.excerpt,
            status: post.status,
            type: post.type,
            feature_image: post.feature_image,
            author: post.author,
            author_slug: post.author_slug,
            published_at: post.published_at,
            version: post.version,
          }
        : emptyDraft()
      tagText.value = post?.tags.map((tag) => tag.name).join(', ') ?? ''
      baseline.value = snapshot()
      ready.value = true
    } catch (cause) {
      if (sequence === loadSequence) error.value = errorMessage(cause)
    } finally {
      if (sequence === loadSequence) loading.value = false
    }
  }

  watch(
    () => route.params.id,
    () => {
      if (id.value && route.params.id === id.value) return
      void load()
    },
    { immediate: true },
  )
  watch(
    () => model.value.title,
    (title) => {
      if (automaticSlug.value) model.value.slug = slugify(title)
    },
  )
  watch([() => model.value.body, () => model.value.format, mode], () => {
    if (mode.value === 'write') {
      previewTask.cancel()
      previewing.value = false
      return
    }
    previewing.value = true
    previewError.value = ''
    previewTask.schedule(async (signal) => {
      try {
        const result = await previewPost(model.value.body, model.value.format, signal)
        if (signal.aborted) return
        html.value = result.html
        previewError.value = ''
      } catch (cause) {
        if (!signal.aborted) previewError.value = errorMessage(cause)
      } finally {
        if (!signal.aborted) previewing.value = false
      }
    })
  })

  async function save(status: PostInput['status'] = model.value.status): Promise<void> {
    if (busy.value || loading.value || !ready.value) return
    if (String(route.params.id || '') !== id.value) return
    const sequence = loadSequence
    busy.value = true
    error.value = ''
    try {
      const originalSlug = model.value.slug
      const submitted = {
        ...model.value,
        status,
        slug: originalSlug.trim() || slugify(model.value.title),
      }
      const submittedTagText = tagText.value
      const payload: PostInput = {
        ...submitted,
        tags: submittedTagText
          .split(/[,，]/)
          .map((tag) => tag.trim())
          .filter(Boolean),
      }
      const post = await savePost(payload, id.value || undefined)
      if (sequence !== loadSequence) return
      id.value = post.id
      previewShared.value = post.preview_shared
      automaticSlug.value = false
      model.value = {
        ...model.value,
        status: post.status,
        slug: model.value.slug === originalSlug ? post.slug : model.value.slug,
        version: post.version,
        published_at: post.published_at,
      }
      baseline.value = JSON.stringify([
        {
          ...submitted,
          status: post.status,
          slug: post.slug,
          version: post.version,
          published_at: post.published_at,
        },
        submittedTagText,
      ])
      notify(
        dirty.value
          ? 'Saved. Newer edits are still unsaved.'
          : status === 'published'
            ? 'Post published. Changes saved.'
            : 'Draft saved',
      )
      if (!route.params.id) await router.replace(`/workspace/posts/${post.id}`)
    } catch (cause) {
      if (sequence === loadSequence) error.value = errorMessage(cause)
    } finally {
      busy.value = false
    }
  }

  async function setPreviewSharing(enabled: boolean): Promise<void> {
    const postId = id.value
    if (busy.value || !ready.value || !postId || route.params.id !== postId) return
    if (model.value.status !== 'draft') return
    const sequence = loadSequence
    busy.value = true
    error.value = ''
    try {
      const sharing = await setDraftPreview(postId, enabled)
      if (sequence === loadSequence) {
        previewShared.value = sharing.enabled
        notify(sharing.enabled ? 'Preview link enabled' : 'Preview link disabled')
      }
    } catch (cause) {
      if (sequence === loadSequence) error.value = errorMessage(cause)
    } finally {
      busy.value = false
    }
  }

  function insertImage(url: string, alt: string, range: [number, number]): void {
    const insertion = `\n${imageMarkup(url, alt, model.value.format)}\n`
    const start = Math.min(range[0], model.value.body.length)
    const end = Math.min(range[1], model.value.body.length)
    model.value.body = model.value.body.slice(0, start) + insertion + model.value.body.slice(end)
    void nextTick(() => {
      textarea.value?.focus({ preventScroll: true })
      textarea.value?.setSelectionRange(start + insertion.length, start + insertion.length)
    })
  }

  function openLibrary(): void {
    if (busy.value || !ready.value) return
    selection = [
      textarea.value?.selectionStart ?? model.value.body.length,
      textarea.value?.selectionEnd ?? model.value.body.length,
    ]
    libraryOpen.value = true
  }

  function selectImage(image: LibraryImage, alt: string): void {
    if (!ready.value || busy.value) return
    if (mode.value === 'preview') mode.value = 'write'
    insertImage(image.url, alt, selection)
    libraryOpen.value = false
  }

  function beforeUnload(event: BeforeUnloadEvent): void {
    if (!dirty.value && !busy.value) return
    event.preventDefault()
    event.returnValue = ''
  }
  const canLeave = (to: RouteLocationNormalized): boolean => {
    if (id.value && to.params.id === id.value) return true
    if (busy.value) {
      notify('Wait for the save to finish before leaving this page.')
      return false
    }
    return !dirty.value || confirm('You have unsaved changes. Leave this page?')
  }
  onBeforeRouteLeave(canLeave)
  onBeforeRouteUpdate(canLeave)
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => {
    loadSequence++
    window.removeEventListener('beforeunload', beforeUnload)
  })

  return {
    model,
    id,
    tagText,
    tags,
    mode,
    html,
    loading,
    ready,
    busy,
    libraryOpen,
    openLibrary,
    selectImage,
    error,
    previewError,
    previewing,
    previewShared,
    setPreviewSharing,
    dirty,
    automaticSlug,
    save,
    load,
  }
}
