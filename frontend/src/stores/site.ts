import { ref } from 'vue'
import { getAdminSite, getSite } from '../api/site'
import type { Site } from '../types'
import { initialDocument } from './initial'

export const site = ref<Site>(
  initialDocument.site ?? {
    title: '无情老小儿',
    description: '',
    cover: '',
    logo: '',
    author: 'xionzhi',
    author_image: '',
    author_bio: '',
    navigation: [],
    posts_per_page: 5,
  },
)

export async function loadSite(admin = false): Promise<void> {
  site.value = await (admin ? getAdminSite() : getSite())
}
