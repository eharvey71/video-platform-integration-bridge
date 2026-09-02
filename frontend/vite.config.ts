import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Flask app serves the built bundle from frontend/dist, so asset URLs stay
// root-relative. In dev, everything the SPA calls is proxied to Flask on 8000 so
// the browser still sees a single origin and the session cookie just works --
// no CORS, which is why config.py ships with an empty CORS allowlist.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      ['/adminapi', '/auth', '/canvas', '/api', '/zoomapi', '/logs'].map((p) => [
        p,
        { target: 'http://127.0.0.1:8000', changeOrigin: false },
      ]),
    ),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
