import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
       manualChunks(id) {
      if (!id.includes('node_modules')) return;
      if (id.includes('react') || id.includes('react-dom')) return 'vendor-react';
      if (id.includes('three')) return 'vendor-three';
      if (id.includes('recharts') || id.includes('d3')) return 'vendor-charts';
      if (id.includes('lodash')) return 'vendor-lodash';
      if (id.includes('axios')) return 'vendor-axios';
      // fallback: group remaining node_modules into 'vendor'
      return 'vendor';
}
      }
    }
  },
  server: {
    port: 3000,
    open: true
  }
})
