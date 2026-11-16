import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import {
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
  useRoute,
  useRouter,
  type RouteLocationNormalized,
} from 'vue-router'
import { getAdminPost, previewPost, savePost, type PostInput } from '../api/posts'
import { getAdminTags } from '../api/tags'
import { uploadImage } from '../api/media'
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
  const busy = ref(false)
  const uploading = ref(false)
  const error = ref('')
  const previewError = ref('')
  const previewing = ref(false)
  const automaticSlug = ref(true)
  const previewTask = useDebouncedTask(350)
  let loadSequence = 0

  const snapshot = (): string => JSON.stringify([model.value, tagText.value])
  const dirty = computed(() => Boolean(baseline.value) && snapshot() !== baseline.value)

  async function load(): Promise<void> {
    const sequence = ++loadSequence
    loading.value = true
    error.value = ''
    try {
      const [availableTags, post] = await Promise.all([
        getAdminTags(),
        route.params.id ? getAdminPost(String(route.params.id)) : Promise.resolve(undefined),
      ])
      if (sequence !== loadSequence) return
      tags.value = availableTags
      automaticSlug.value = !post
      id.value = post?.id ?? ''
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
    if (busy.value) return
    busy.value = true
    error.value = ''
    try {
      const originalSlug = model.value.slug
      const submitted = {
        ...model.value,
        status,
        slug: model.value.slug || slugify(model.value.title),
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
      id.value = post.id
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
      error.value = errorMessage(cause)
    } finally {
      busy.value = false
    }
  }

  async function upload(event: Event, cover: boolean): Promise<void> {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    uploading.value = true
    error.value = ''
    try {
      const { url } = await uploadImage(file)
      if (cover) model.value.feature_image = url
      else {
        const insertion =
          model.value.format === 'markdown'
            ? `\n![Image](${url})\n`
            : `\n<img src="${url}" alt="Image">\n`
        const start = textarea.value?.selectionStart ?? model.value.body.length
        const end = textarea.value?.selectionEnd ?? start
        model.value.body =
          model.value.body.slice(0, start) + insertion + model.value.body.slice(end)
      }
    } catch (cause) {
      error.value = errorMessage(cause)
    } finally {
      uploading.value = false
      input.value = ''
    }
  }

  function beforeUnload(event: BeforeUnloadEvent): void {
    if (!dirty.value) return
    event.preventDefault()
    event.returnValue = ''
  }
  const canLeave = (to: RouteLocationNormalized): boolean =>
    Boolean(id.value && to.params.id === id.value) ||
    !dirty.value ||
    confirm('You have unsaved changes. Leave this page?')
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
    busy,
    uploading,
    error,
    previewError,
    previewing,
    dirty,
    automaticSlug,
    save,
    upload,
  }
}
