import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/search': 'http://localhost:8000',
      '/disambiguate': 'http://localhost:8000',
      '/trace': 'http://localhost:8000',
      '/faculty': 'http://localhost:8000',
      '/slots': 'http://localhost:8000',
      '/draft-email': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
      '/teacher': 'http://localhost:8000',
      '/student-request': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/departments': 'http://localhost:8000',
      '/eval-reports': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/events': 'http://localhost:8000',
    }
  }
})
