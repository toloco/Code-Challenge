import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const bffTarget = process.env.VITE_BFF_URL ?? 'http://localhost:3001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/copilotkit': {
        target: bffTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      '/copilotkit': {
        target: bffTarget,
        changeOrigin: true,
      },
    },
  },
})
