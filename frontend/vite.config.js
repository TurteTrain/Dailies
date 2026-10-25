import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Use 127.0.0.1 everywhere (not "localhost") so cookies and the Spotify redirect URI line up.
    host: '127.0.0.1',
    port: 5173,
    // The browser talks only to Vite; Vite forwards these paths to Django.
    // That makes React and Django look like one origin: no CORS setup, and session cookies just work.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/spotify': 'http://127.0.0.1:8000',
    },
  },
})
