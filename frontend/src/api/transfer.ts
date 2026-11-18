import { api, queryString } from './request'

export const MAX_JSON_BYTES = 16 * 1024 * 1024

export interface ImportPreview {
  sha256: string
  posts: number
  pages: number
  tags: number
  files: number
  ignored_files: number
  new_posts: number
  skipped_posts: number
  new_tags: number
  missing_files: string[]
  changed_files: string[]
  conflicts: string[]
  can_import: boolean
  can_skip_conflicts: boolean
}

export interface ImportResult {
  imported_posts: number
  imported_tags: number
  skipped_posts: number
  skipped_conflicts: number
  settings_imported: boolean
}

export async function exportData(signal?: AbortSignal): Promise<Blob> {
  const data = await api<unknown>('/admin/data/export', { signal })
  return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
}

export const previewData = (content: string, signal?: AbortSignal): Promise<ImportPreview> =>
  api('/admin/data/preview', { method: 'POST', body: content, signal })

export const importData = (
  content: string,
  sha256: string,
  includeSettings: boolean,
  skipConflicts: boolean,
): Promise<ImportResult> =>
  api(
    `/admin/data/import?${queryString({ sha256, include_settings: includeSettings, skip_conflicts: skipConflicts })}`,
    { method: 'POST', body: content },
  )
