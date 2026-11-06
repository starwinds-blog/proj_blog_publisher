import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 8500,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8501',
        changeOrigin: true,
      },
    },
  },
})
