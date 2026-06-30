import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Allows imports like: import { useAuth } from '@/context/AuthContext'
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // In dev, forward /api requests to the Django container (CORS-free).
      // In production, /api/* routes to EB via CloudFront path routing.
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
