import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          if (id.includes('three')) return 'vendor-three'
          if (id.includes('recharts') || id.includes('d3')) return 'vendor-charts'
          return
        }
      }
    }
  },
  server: {
    port: 3000,
    open: true
  }
})
