import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/search': 'http://127.0.0.1:5001',
      '/tags': 'http://127.0.0.1:5001',
      '/pdf': 'http://127.0.0.1:5001',
      '/reindex': 'http://127.0.0.1:5001',
      '/stats': 'http://127.0.0.1:5001',
      '/export': 'http://127.0.0.1:5001',
      '/companies': 'http://127.0.0.1:5001',
      '/tag_values': 'http://127.0.0.1:5001',
      '/rename_tag': 'http://127.0.0.1:5001',
      '/bulk_tags': 'http://127.0.0.1:5001',
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: false,
  },
})
