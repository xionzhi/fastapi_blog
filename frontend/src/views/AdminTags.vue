<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Plus, Pencil, Trash2, X } from 'lucide-vue-next'
import { slugify } from '../utils/format'
import { useScrollLock } from '../composables/useScrollLock'
import { useModalFocus } from '../composables/useModalFocus'
import { useTagManagement } from '../composables/useTagManagement'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const {
  tags,
  editing,
  id,
  form,
  busy,
  loading,
  pageError,
  formError,
  deleteError,
  deleteTarget,
  load,
  edit,
  closeEditor,
  save,
  askToDelete,
  cancelDelete,
  remove,
} = useTagManagement()
useScrollLock(editing)
const dialog = ref<HTMLElement>()
const newTagButton = ref<HTMLButtonElement>()
const { keyboard } = useModalFocus(editing, dialog, closeEditor)
async function confirmDelete(): Promise<void> {
  if (!(await remove())) return
  await nextTick()
  newTagButton.value?.focus({ preventScroll: true })
}
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
        ref="newTagButton"
        class="button-primary"
        :disabled="busy || loading"
        @click="edit()"
      >
        <Plus :size="17" />
        New tag
      </button>
    </header>
    <p
      v-if="pageError"
      class="form-error"
      role="alert"
    >
      {{ pageError }}
      <button
        class="text-button"
        :disabled="busy || loading"
        @click="load"
      >
        Try again
      </button>
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
        :inert="loading || busy ? true : undefined"
      >
        <div>
          <strong>{{ tag.name }}</strong>
          <small>/tag/{{ tag.slug }}/</small>
        </div>
        <span>{{ tag.count ?? 0 }} {{ tag.count === 1 ? 'post' : 'posts' }}</span>
        <div class="row-actions">
          <button
            class="icon-button"
            :aria-label="`Edit ${tag.name}`"
            :disabled="busy || loading"
            @click="edit(tag)"
          >
            <Pencil :size="16" />
          </button>
          <button
            class="icon-button danger-hover"
            :aria-label="`Delete ${tag.name}`"
            :disabled="busy || loading"
            @click="askToDelete(tag)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
      <p
        v-if="!loading && !pageError && !tags.length"
        class="panel-message muted"
      >
        No tags yet. You can also create them while writing.
      </p>
    </div>
    <Teleport to="body">
      <div
        v-if="editing"
        class="admin admin-modal-backdrop"
        @click.self="closeEditor"
        @keydown="keyboard"
      >
        <section
          ref="dialog"
          class="admin-modal"
          tabindex="-1"
          role="dialog"
          aria-modal="true"
          :aria-label="id ? 'Edit tag' : 'New tag'"
        >
          <header>
            <h2>{{ id ? 'Edit tag' : 'New tag' }}</h2>
            <button
              class="icon-button"
              aria-label="Close"
              :disabled="busy"
              @click="closeEditor"
            >
              <X :size="20" />
            </button>
          </header>
          <form @submit.prevent="save">
            <label>
              Name
              <input
                v-model="form.name"
                :disabled="busy"
                @input="!id && (form.slug = slugify(form.name))"
                required
                maxlength="80"
              />
            </label>
            <label>
              URL
              <input
                v-model="form.slug"
                :disabled="busy"
                required
                maxlength="200"
              />
            </label>
            <label>
              Description
              <textarea
                v-model="form.description"
                :disabled="busy"
                rows="3"
                maxlength="1000"
              />
            </label>
            <p
              v-if="formError"
              class="form-error"
              role="alert"
            >
              {{ formError }}
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
    <ConfirmDialog
      v-if="deleteTarget"
      title="Delete tag?"
      :item-name="deleteTarget.name"
      description="This tag will be removed from all posts. Your posts will be kept. This cannot be undone."
      confirm-label="Delete tag"
      :busy="busy"
      :error="deleteError"
      @cancel="cancelDelete"
      @confirm="confirmDelete"
    />
  </div>
</template>
