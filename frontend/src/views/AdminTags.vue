<script setup lang="ts">
import { deleteTag, getAdminTags, saveTag } from '../api/tags'

import { ref } from 'vue'
import { Plus, Pencil, Trash2, X } from 'lucide-vue-next'
import { errorMessage, slugify } from '../utils/format'
import { notify } from '../stores/notifications'
import { useScrollLock } from '../composables/useScrollLock'
import { useModalFocus } from '../composables/useModalFocus'
import type { Tag } from '../types'
const tags = ref<Tag[]>([])
const editing = ref(false)
useScrollLock(editing)
const id = ref('')
const form = ref({ name: '', slug: '', description: '' })
const busy = ref(false)
const error = ref('')
const loading = ref(true)
const dialog = ref<HTMLElement>()
function close(): void {
  if (!busy.value) editing.value = false
}
const { keyboard } = useModalFocus(editing, dialog, close)
async function load() {
  loading.value = true
  try {
    tags.value = await getAdminTags()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
function edit(tag?: Tag) {
  id.value = tag?.id || ''
  form.value = { name: tag?.name || '', slug: tag?.slug || '', description: tag?.description || '' }
  editing.value = true
  error.value = ''
}
async function save() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await saveTag(form.value, id.value || undefined)
    editing.value = false
    await load()
    notify('Tag saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function remove(tag: Tag) {
  if (!confirm(`Delete tag "${tag.name}"? Posts will be kept.`)) return
  try {
    await deleteTag(tag.id)
    await load()
    notify('Tag deleted')
  } catch (e) {
    error.value = errorMessage(e)
  }
}
load()
</script>
<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div>
        <p class="eyebrow">ORGANIZE YOUR IDEAS</p>
        <h1>Tags</h1>
        <p class="muted">Connect your posts through shared ideas.</p>
      </div>
      <button
        class="button-primary"
        @click="edit()"
      >
        <Plus :size="17" />
        New tag
      </button>
    </header>
    <p
      v-if="error && !editing"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
    <div
      class="content-panel tag-table public-results"
      :aria-busy="loading"
    >
      <p
        v-if="loading"
        class="refresh-status muted"
        role="status"
      >
        Loading tags…
      </p>
      <div
        v-for="tag in tags"
        :key="tag.id"
        class="tag-table-row"
        :inert="loading ? true : undefined"
      >
        <div>
          <strong>{{ tag.name }}</strong>
          <small>/tag/{{ tag.slug }}/</small>
        </div>
        <span>{{ tag.count }} posts</span>
        <div class="row-actions">
          <button
            class="icon-button"
            :aria-label="`Edit ${tag.name}`"
            @click="edit(tag)"
          >
            <Pencil :size="16" />
          </button>
          <button
            class="icon-button danger-hover"
            :aria-label="`Delete ${tag.name}`"
            @click="remove(tag)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
      <p
        v-if="!loading && !error && !tags.length"
        class="panel-message muted"
      >
        No tags yet. You can also create them while writing.
      </p>
    </div>
    <Teleport to="body">
      <div
        v-if="editing"
        class="admin-modal-backdrop"
        @click.self="close"
        @keydown="keyboard"
      >
        <section
          ref="dialog"
          class="admin-modal"
          tabindex="-1"
          role="dialog"
          aria-modal="true"
          aria-label="Edit tag"
        >
          <header>
            <h2>{{ id ? 'Edit tag' : 'New tag' }}</h2>
            <button
              class="icon-button"
              aria-label="Close"
              :disabled="busy"
              @click="close"
            >
              <X :size="20" />
            </button>
          </header>
          <form @submit.prevent="save">
            <label>
              Name
              <input
                v-model="form.name"
                @input="!id && (form.slug = slugify(form.name))"
                required
                maxlength="80"
              />
            </label>
            <label>
              URL
              <input
                v-model="form.slug"
                required
                maxlength="200"
              />
            </label>
            <label>
              Description
              <textarea
                v-model="form.description"
                rows="3"
                maxlength="1000"
              />
            </label>
            <p
              v-if="error"
              class="form-error"
              role="alert"
            >
              {{ error }}
            </p>
            <button
              class="button-primary"
              :disabled="busy"
            >
              {{ busy ? 'Saving…' : 'Save tag' }}
            </button>
          </form>
        </section>
      </div>
    </Teleport>
  </div>
</template>
