import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Echoes runs on different ports than Hot Take Duel so both can be up at once.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
