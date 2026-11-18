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
  canProceed,
  includeSettings,
  skipConflicts,
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
    <h2>Export and import data</h2>
    <p>
      Export articles, pages, tags, redirects and site settings as JSON. File references are
      relative to the project root. Copy referenced image files separately.
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
      <label
        class="button-secondary transfer-file"
        :class="{ 'is-disabled': busy }"
      >
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
    <p
      v-if="filename"
      class="muted transfer-filename"
    >
      Selected file: {{ filename }}
    </p>
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
        {{ preview.files }} referenced image files
      </p>
      <p>
        {{ preview.new_posts }} new content items · {{ preview.skipped_posts }} identical content
        items skipped · {{ preview.new_tags }} new tags
      </p>
      <div
        v-if="preview.conflicts.length || preview.changed_files.length"
        class="transfer-warning"
        role="alert"
      >
        <p v-if="preview.conflicts.length">
          {{ preview.conflicts.length }}
          {{ preview.conflicts.length === 1 ? 'entry conflicts' : 'entries conflict' }}
          with existing content or depend on a conflicting entry.
          <template v-if="preview.can_skip_conflicts && !skipConflicts">
            Select “Skip conflicting entries” to import the remaining content.
          </template>
        </p>
        <p v-if="preview.changed_files.length">
          {{ preview.changed_files.length }}
          {{ preview.changed_files.length === 1 ? 'image differs' : 'images differ' }}
          from the export. Copy the matching files and preview the import again.
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
      <label
        v-if="preview.can_skip_conflicts"
        class="transfer-checkbox"
      >
        <input
          v-model="skipConflicts"
          type="checkbox"
          :disabled="busy"
        />
        Skip conflicting entries and keep existing content
      </label>
      <div v-if="preview.missing_files.length">
        <p>
          {{ preview.missing_files.length }}
          {{ preview.missing_files.length === 1 ? 'image file is' : 'image files are' }}
          missing. New articles will use placeholders for missing inline images and omit missing
          covers. You can copy these files before importing to keep the images.
        </p>
        <ul>
          <li
            v-for="path in preview.missing_files.slice(0, 10)"
            :key="path"
          >
            {{ path }}
          </li>
        </ul>
      </div>
      <p v-if="preview.ignored_files">
        {{ preview.ignored_files }} unused
        {{ preview.ignored_files === 1 ? 'file will' : 'files will' }} be skipped.
      </p>
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
      <p v-if="canProceed && !confirmed">
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
      class="transfer-result"
      role="status"
    >
      Import complete. Added {{ result.imported_posts }}
      {{ result.imported_posts === 1 ? 'content item' : 'content items' }} and
      {{ result.imported_tags }} {{ result.imported_tags === 1 ? 'tag' : 'tags' }}.
      <template v-if="result.skipped_posts">
        Skipped {{ result.skipped_posts }} identical
        {{ result.skipped_posts === 1 ? 'content item' : 'content items' }}.
      </template>
      <template v-if="result.skipped_conflicts">
        {{ result.skipped_conflicts }} conflicting
        {{ result.skipped_conflicts === 1 ? 'entry' : 'entries' }} skipped.
      </template>
      {{
        result.settings_imported ? 'Site settings were imported.' : 'Site settings were preserved.'
      }}
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
  gap: 12px;
  flex-wrap: wrap;
  margin: 24px 0;
}
.transfer-file {
  position: relative;
  cursor: pointer;
  min-width: 0;
  max-width: 100%;
  white-space: normal;
}
.transfer-file.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
.transfer-file input:disabled {
  cursor: not-allowed;
}
.transfer-filename {
  overflow-wrap: anywhere;
}
.transfer-preview {
  border-top: 1px solid var(--line);
  padding-top: 24px;
}
.transfer-preview h3 {
  font-size: 16px;
}
.transfer-preview ul {
  font-size: 12px;
  overflow-wrap: anywhere;
}
.transfer-warning {
  padding: 12px 16px;
  border: 1px solid var(--admin-warn-line);
  border-radius: 6px;
  background: var(--admin-warn-bg);
  color: var(--admin-warn-text);
}
.transfer-warning ul {
  margin: 0;
}
.data-transfer .transfer-result {
  margin: 20px 0 0;
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--admin-selected);
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
