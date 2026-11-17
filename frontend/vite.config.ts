import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  build: { manifest: true },
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      ['/api', '/content/images', '/rss', '/sitemap.xml', '/robots.txt'].map((path) => [
        path,
        'http://127.0.0.1:8000',
      ]),
    ),
  },
})
