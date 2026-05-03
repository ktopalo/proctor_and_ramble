// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/question': 'http://127.0.0.1:8000',
      '/session': 'http://127.0.0.1:8000',
    },
  },
})
