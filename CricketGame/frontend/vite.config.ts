import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0', // Allow LAN connections
    proxy: {
      "/auth": "http://localhost:8000",
      "/api": "http://localhost:8000",
      "/rooms": "http://localhost:8000",
      "/network": "http://localhost:8000",
      "/ws": {
        target: "http://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
