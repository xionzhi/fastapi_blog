import { watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { site } from '../stores/site'
import { updatePageMetadata, type PageMetadata } from '../utils/metadata'

export function usePageMetadata(details: () => PageMetadata): void {
  const route = useRoute()
  watchEffect(() => updatePageMetadata(route.path, site.value, details()))
}
