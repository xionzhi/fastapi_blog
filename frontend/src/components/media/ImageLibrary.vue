<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Copy, Image, RefreshCw, Trash2, Upload, X } from 'lucide-vue-next'
import type { LibraryImage } from '../../api/media'
import { useImageLibrary } from '../../composables/useImageLibrary'
import { useModalFocus } from '../../composables/useModalFocus'
import { useScrollLock } from '../../composables/useScrollLock'
import { notify } from '../../stores/notifications'
import { date } from '../../utils/format'
import { fileSize, imageAlt, imageMarkup } from '../../utils/images'

const props = defineProps<{ picker?: boolean }>()
const emit = defineEmits<{
  select: [image: LibraryImage | undefined]
  busy: [value: boolean]
  loading: [value: boolean]
}>()
const { search, page, data, loading, busy, error, selected, reload, upload, move, remove } =
  useImageLibrary()
const file = ref<HTMLInputElement>()
const newPath = ref('')
const failed = ref<Record<string, boolean>>({})
const dialog = ref<HTMLElement>()
const detailsOpen = computed(() => !!selected.value && !props.picker)
useScrollLock(detailsOpen)
function closeDetails(): void {
  if (!busy.value) selected.value = undefined
}
const { keyboard } = useModalFocus(detailsOpen, dialog, closeDetails)
watch(busy, (value) => emit('busy', value), { flush: 'sync' })
watch(loading, (value) => emit('loading', value), { immediate: true, flush: 'sync' })
watch(selected, (image) => {
  newPath.value = image?.path ?? ''
  if (props.picker) emit('select', image)
})

function choose(image: LibraryImage): void {
  selected.value = image
}
function savePath(): void {
  if (selected.value) void move(selected.value, newPath.value.trim())
}
async function copy(value: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value)
    notify('Copied to clipboard')
  } catch {
    notify('Clipboard unavailable. Select and copy the image URL manually.')
  }
}
function confirmDelete(image: LibraryImage): void {
  if (
    confirm(
      `Permanently delete "${image.path}"? This cannot be undone. Unsaved edits and external references are not checked.`,
    )
  ) {
    void remove(image)
  }
}
</script>

<template>
  <div class="image-library">
    <div class="media-toolbar">
      <label class="media-search">
        Search images
        <input
          v-model="search"
          type="search"
          placeholder="Filename or folder"
          maxlength="200"
          :disabled="busy"
        />
      </label>
      <button
        type="button"
        class="button-secondary"
        :disabled="busy || loading"
        @click="reload"
      >
        <RefreshCw :size="16" />
        Refresh
      </button>
      <button
        type="button"
        class="button-primary"
        :disabled="busy || loading"
        @click="file?.click()"
      >
        <Upload :size="16" />
        {{ busy ? 'Working…' : 'Upload image' }}
      </button>
      <input
        ref="file"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        hidden
        @change="upload"
      />
    </div>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
    <div class="media-layout">
      <div
        class="media-results"
        :aria-busy="loading"
      >
        <p
          class="media-status muted"
          role="status"
        >
          {{
            loading
              ? 'Loading images…'
              : `${data?.total ?? 0} ${data?.total === 1 ? 'image' : 'images'}`
          }}
        </p>
        <div
          class="media-grid"
          :inert="loading || busy ? true : undefined"
        >
          <button
            v-for="image in data?.items"
            :key="image.path"
            :title="image.path"
            type="button"
            class="media-card"
            :class="{ selected: selected?.path === image.path }"
            :aria-pressed="selected?.path === image.path"
            @click="choose(image)"
          >
            <span class="media-thumbnail">
              <img
                v-if="!failed[image.path]"
                :src="image.thumbnail"
                alt=""
                width="480"
                height="360"
                loading="lazy"
                decoding="async"
                @error="failed[image.path] = true"
              />
              <Image
                v-else
                :size="32"
                aria-label="Preview unavailable"
              />
            </span>
            <strong>{{ image.name }}</strong>
            <small>
              {{ fileSize(image.size) }} ·
              {{ image.usages.length ? 'In use' : 'No saved references' }}
            </small>
          </button>
        </div>
        <p
          v-if="!loading && !data?.items.length"
          class="panel-message muted"
        >
          {{ search ? 'No matching images.' : 'No images yet. Upload an image to get started.' }}
        </p>
        <nav
          v-if="data && data.pages > 1"
          class="media-pagination"
          aria-label="Image pagination"
        >
          <button
            type="button"
            class="button-secondary"
            :disabled="loading || busy || page <= 1"
            @click="page--"
          >
            Previous
          </button>
          <span>Page {{ page }} of {{ data.pages }}</span>
          <button
            type="button"
            class="button-secondary"
            :disabled="loading || busy || page >= data.pages"
            @click="page++"
          >
            Next
          </button>
        </nav>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="selected && !picker"
        class="admin admin-modal-backdrop"
        @click.self="closeDetails"
        @keydown="keyboard"
      >
        <section
          ref="dialog"
          class="admin-modal media-details"
          role="dialog"
          aria-modal="true"
          aria-labelledby="image-details-title"
          tabindex="-1"
        >
          <header>
            <h2 id="image-details-title">Image details</h2>
            <button
              type="button"
              class="icon-button"
              aria-label="Close image details"
              :disabled="busy"
              @click="closeDetails"
            >
              <X :size="20" />
            </button>
          </header>
          <p
            v-if="error"
            class="form-error"
            role="alert"
          >
            {{ error }}
          </p>
          <p class="muted">{{ fileSize(selected.size) }} · {{ date(selected.modified_at) }}</p>
          <label>
            Image URL
            <input
              :value="selected.url"
              readonly
              @focus="($event.target as HTMLInputElement).select()"
            />
          </label>
          <div class="media-actions">
            <button
              type="button"
              class="button-secondary"
              @click="copy(selected.url)"
            >
              <Copy :size="14" />
              Copy URL
            </button>
            <button
              type="button"
              class="button-secondary"
              @click="copy(imageMarkup(selected.url, imageAlt(selected), 'markdown'))"
            >
              Copy Markdown
            </button>
            <a
              :href="selected.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-button"
            >
              Open original ↗
            </a>
          </div>
          <form @submit.prevent="savePath">
            <label>
              Filename and folder
              <input
                v-model="newPath"
                required
                maxlength="500"
                :disabled="busy"
                placeholder="2026/11/photo.png"
              />
            </label>
            <p class="muted">
              Relative to the image directory. Saved post and site references are updated. External
              links and unsaved edits are not updated.
            </p>
            <button
              class="button-primary"
              :disabled="busy || loading || !newPath.trim() || newPath.trim() === selected.path"
            >
              Save path
            </button>
          </form>
          <div class="media-usage">
            <h3>Used by</h3>
            <ul v-if="selected.usages.length">
              <li
                v-for="usage in selected.usages"
                :key="usage.url + usage.title"
              >
                <RouterLink :to="usage.url">{{ usage.title }}</RouterLink>
              </li>
            </ul>
            <p
              v-else
              class="muted"
            >
              No saved article or site references found.
            </p>
          </div>
          <button
            type="button"
            class="button-secondary media-delete"
            :disabled="busy || loading || !!selected.usages.length"
            @click="confirmDelete(selected)"
          >
            <Trash2 :size="16" />
            Delete image
          </button>
          <p
            v-if="selected.usages.length"
            class="muted"
          >
            Remove saved references before deleting this image.
          </p>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.media-toolbar,
.media-actions,
.media-pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.media-toolbar {
  margin-bottom: 18px;
  align-items: end;
}
.media-search {
  flex: 1;
  min-width: 180px;
}
.media-layout {
  display: grid;
  gap: 24px;
}
.media-results {
  min-width: 0;
  min-height: 280px;
}
.media-status {
  min-height: 22px;
  margin: 0 0 12px;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}
.media-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  min-width: 0;
  padding: 0;
  border: 1px solid #dfe5de;
  border-radius: 7px;
  background: #fff;
  text-align: left;
  color: #38483c;
  gap: 0;
  overflow: hidden;
  text-transform: none;
  letter-spacing: normal;
  font-weight: 400;
}
.media-card:hover,
.media-card.selected {
  border-color: var(--green);
}
.media-card.selected {
  box-shadow: inset 0 0 0 1px var(--green);
}
.media-thumbnail {
  aspect-ratio: 4 / 3;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}
.media-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.media-card strong {
  font-size: 12px;
  line-height: 1.5;
  padding: 10px 12px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.media-card small {
  margin-top: auto;
  padding: 6px 12px 10px;
}
.media-pagination {
  justify-content: space-between;
  margin-top: 22px;
  font-size: 12px;
}
.media-details {
  min-width: 0;
  padding: 20px;
  border: 1px solid #dfe5de;
  border-radius: 8px;
  background: #fff;
  align-self: auto;
  max-width: 560px;
  max-height: calc(100dvh - 50px);
  overflow: auto;
}
.media-details h2 {
  font-size: 17px;
  margin: 0 0 10px;
}
.media-details h3 {
  font-size: 14px;
  margin: 0 0 10px;
}
.media-actions {
  margin: 16px 0 24px;
}
.media-actions button {
  font-size: 10px;
  padding: 8px 10px;
}
.media-details form p {
  margin: 12px 0;
}
.media-usage {
  margin: 24px 0;
  border-top: 1px solid #e4e9e1;
  padding-top: 18px;
}
.media-usage ul {
  padding-left: 18px;
  margin: 0;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.media-delete {
  color: #aa3941;
}
@media (max-width: 520px) {
  .media-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .media-search {
    flex-basis: 100%;
  }
  .media-toolbar {
    gap: 8px;
  }
}
</style>
