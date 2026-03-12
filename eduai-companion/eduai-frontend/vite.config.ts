import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"
import { VitePWA } from "vite-plugin-pwa"

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2,webp}"],
        runtimeCaching: [
          {
            // Cache Chat, Quiz, and other API calls (network-first for fresh data)
            urlPattern: /^https:\/\/lumnos-backend\.onrender\.com\/api/,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: { maxEntries: 100, maxAgeSeconds: 300 },
              networkTimeoutSeconds: 10,
            },
          },
          {
            // Cache Google Fonts
            urlPattern: /^https:\/\/fonts\.googleapis\.com/,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "google-fonts-stylesheets" },
          },
          {
            // Cache Clerk assets
            urlPattern: /^https:\/\/.*\.clerk\./,
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "clerk-assets",
              expiration: { maxEntries: 30, maxAgeSeconds: 86400 },
            },
          },
        ],
      },
      manifest: {
        name: "Lumnos — Dein KI-Lerncoach",
        short_name: "Lumnos",
        description: "KI-Tutor für deutsche Schüler: 16 Fächer, Quiz, Abitur-Simulation, Karteikarten & mehr",
        theme_color: "#6366f1",
        background_color: "#0f172a",
        display: "standalone",
        orientation: "portrait-primary",
        start_url: "/",
        scope: "/",
        lang: "de",
        categories: ["education", "productivity"],
        icons: [
          {
            src: "pwa-192x192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
    }),
  ],
  server: {
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    include: ['@clerk/clerk-react', '@clerk/shared', 'react', 'react-dom'],
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-framer": ["framer-motion"],
        },
      },
    },
    minify: "esbuild",
  },
})

