<script setup lang="ts">
import { Download, Upload } from 'lucide-vue-next'
import { useDataTransfer } from '../composables/useDataTransfer'

const {
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
} = useDataTransfer()
const emit = defineEmits<{ imported: [settingsImported: boolean] }>()
async function importContent(): Promise<void> {
  await apply()
  if (result.value) emit('imported', result.value.settings_imported)
}
</script>
<template>
  <section class="content-panel settings-section data-transfer">
    <p class="eyebrow">BACKUP AND MIGRATION</p>
    <h2>Export and import data</h2>
    <p>
      Export articles, pages, tags, redirects and site settings as JSON. File references are
      relative to the project root. Copy image files separately.
    </p>
    <p>
      Administrator accounts, passwords, sessions, analytics and SMTP configuration are excluded.
      Imports add new content and reuse identical records. Existing conflicting content is never
      overwritten.
    </p>
    <div class="transfer-actions">
      <button
        type="button"
        class="button-secondary"
        :disabled="busy"
        @click="download"
      >
        <Download :size="16" />
        {{ activity === 'export' ? 'Exporting…' : 'Export JSON' }}
      </button>
      <label class="button-secondary transfer-file">
        <span>
          <Upload :size="16" />
          Choose JSON to preview (up to 16 MB)
        </span>
        <input
          type="file"
          accept=".json,application/json"
          :disabled="busy"
          @change="selectFile"
        />
      </label>
    </div>
    <p v-if="filename">Selected file: {{ filename }}</p>
    <p
      v-if="activity === 'preview'"
      role="status"
    >
      Validating the data and checking image files…
    </p>
    <p
      v-if="error"
      class="form-error"
      role="alert"
    >
      {{ error }}
    </p>
    <div
      v-if="preview"
      class="transfer-preview"
    >
      <h3>Import preview</h3>
      <p>
        {{ preview.posts }} posts · {{ preview.pages }}
        {{ preview.pages === 1 ? 'page' : 'pages' }} · {{ preview.tags }} tags ·
        {{ preview.files }} image files
      </p>
      <p>
        {{ preview.new_posts }} new content items · {{ preview.skipped_posts }} identical content
        items skipped · {{ preview.new_tags }} new tags
      </p>
      <div
        v-if="preview.conflicts.length || preview.changed_files.length"
        role="alert"
      >
        <p>
          Import blocked: {{ preview.conflicts.length }} content conflicts and
          {{ preview.changed_files.length }} changed image files. Resolve these and preview the file
          again.
        </p>
        <ul>
          <li
            v-for="item in [...preview.conflicts, ...preview.changed_files].slice(0, 10)"
            :key="item"
          >
            {{ item }}
          </li>
        </ul>
      </div>
      <div v-if="preview.missing_files.length">
        <p>
          {{ preview.missing_files.length }} image files are missing on this server. Copy them into
          the configured images directory, preserving the paths after the exported media root, then
          preview again.
        </p>
        <ul>
          <li
            v-for="path in preview.missing_files.slice(0, 10)"
            :key="path"
          >
            {{ path }}
          </li>
        </ul>
        <label class="transfer-checkbox">
          <input
            v-model="allowMissingFiles"
            type="checkbox"
            :disabled="busy"
          />
          Import even if image files are missing
        </label>
      </div>
      <label class="transfer-checkbox">
        <input
          v-model="includeSettings"
          type="checkbox"
          :disabled="busy"
        />
        Also import site settings and navigation
      </label>
      <label class="transfer-checkbox">
        <input
          v-model="confirmed"
          type="checkbox"
          :disabled="busy"
        />
        I have reviewed this preview and want to import this data.
      </label>
      <p v-if="preview.can_import && !confirmed">
        Select the confirmation checkbox above before importing.
      </p>
      <button
        type="button"
        class="button-primary"
        :disabled="!canImport"
        @click="importContent"
      >
        {{ activity === 'import' ? 'Importing…' : 'Import data' }}
      </button>
    </div>
    <p
      v-if="result"
      role="status"
    >
      Import completed: {{ result.imported_posts }} content items and
      {{ result.imported_tags }} tags added; {{ result.skipped_posts }} identical content items
      skipped.
      {{
        result.settings_imported ? 'Site settings were imported.' : 'Site settings were preserved.'
      }}
      Administrator accounts were preserved.
    </p>
  </section>
</template>
<style scoped>
.data-transfer {
  margin-top: 36px;
}
.data-transfer p {
  font-size: 13px;
  line-height: 1.9;
}
.transfer-actions {
  display: flex;
  align-items: start;
  gap: 20px;
  flex-wrap: wrap;
  margin: 24px 0;
}
.transfer-file {
  position: relative;
  cursor: pointer;
  min-width: 0;
  max-width: 100%;
}
.transfer-file:focus-within {
  outline: 2px solid var(--green);
  outline-offset: 3px;
}
.transfer-file span {
  display: flex;
  align-items: center;
  gap: 8px;
}
.transfer-file input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  max-width: 100%;
}
.transfer-preview {
  border-top: 1px solid #edf0e9;
  padding-top: 24px;
}
.transfer-preview h3 {
  font-size: 16px;
}
.transfer-preview ul {
  font-size: 12px;
  overflow-wrap: anywhere;
}
.transfer-checkbox {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 10px;
  margin: 18px 0;
  font-size: 12px;
  line-height: 1.7;
}
</style>
