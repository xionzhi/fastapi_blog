<script setup lang="ts">
import { updateSite } from '../api/site'

import { ref } from 'vue'
import { Plus, Trash2, Save } from 'lucide-vue-next'
import { errorMessage } from '../utils/format'
import { site } from '../stores/site'
import { notify } from '../stores/notifications'
import type { Site } from '../types'
import AdminMail from '../components/AdminMail.vue'
import AdminDataTransfer from '../components/AdminDataTransfer.vue'
import ImageField from '../components/media/ImageField.vue'
const cloneSite = () => JSON.parse(JSON.stringify(site.value)) as Site
const form = ref<Site>(cloneSite())
const busy = ref(false)
const error = ref('')
async function save() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    site.value = await updateSite(form.value)
    notify('Site settings saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
function refreshForm(settingsImported: boolean): void {
  if (settingsImported) form.value = cloneSite()
}
</script>
<template>
  <div class="admin-page settings-page">
    <header class="admin-page-heading">
      <div>
        <p class="eyebrow">MAKE IT YOURS</p>
        <h1>Settings</h1>
        <p class="muted">Your blog, your identity, and the words you have written.</p>
      </div>
    </header>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
    <form @submit.prevent="save">
      <section class="content-panel settings-section">
        <h2>Site information</h2>
        <div class="settings-fields">
          <label>
            Site title
            <input
              v-model="form.title"
              required
              maxlength="100"
            />
          </label>
          <label>
            Posts per page
            <input
              v-model.number="form.posts_per_page"
              type="number"
              min="1"
              max="30"
              required
            />
          </label>
          <label class="wide">
            Site description
            <textarea
              v-model="form.description"
              rows="2"
              maxlength="500"
            />
          </label>
          <ImageField
            v-model="form.cover"
            label="Home cover"
            :disabled="busy"
          />
          <ImageField
            v-model="form.logo"
            label="Logo"
            :disabled="busy"
          />
          <label>
            Default author
            <input
              v-model="form.author"
              required
              maxlength="100"
            />
          </label>
          <ImageField
            v-model="form.author_image"
            label="Author image"
            :disabled="busy"
          />
          <label class="wide">
            Author bio
            <textarea
              v-model="form.author_bio"
              rows="2"
              maxlength="500"
            />
          </label>
        </div>
      </section>
      <section class="content-panel settings-section">
        <h2>Navigation</h2>
        <div
          v-for="(item, i) in form.navigation"
          :key="i"
          class="navigation-row"
        >
          <input
            v-model="item.label"
            placeholder="Name"
            :aria-label="`Navigation ${i + 1} label`"
            required
          />
          <input
            v-model="item.url"
            placeholder="URL"
            :aria-label="`Navigation ${i + 1} URL`"
            required
          />
          <button
            type="button"
            class="icon-button"
            :aria-label="`Remove navigation item ${i + 1}`"
            @click="form.navigation.splice(i, 1)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
        <button
          v-if="form.navigation.length < 10"
          type="button"
          class="text-button"
          @click="form.navigation.push({ label: '', url: '' })"
        >
          <Plus :size="16" />
          Add navigation item
        </button>
      </section>
      <button
        class="button-primary"
        :disabled="busy"
      >
        <Save :size="16" />
        {{ busy ? 'Saving…' : 'Save settings' }}
      </button>
    </form>
    <AdminMail />
    <AdminDataTransfer @imported="refreshForm" />
  </div>
</template>
