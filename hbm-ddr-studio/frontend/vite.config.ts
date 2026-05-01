import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  build: {
    // Single-chunk output: avoids any lazy-chunk fetch failures in production.
    // Trades a slightly larger initial bundle for guaranteed-no-stale-chunks.
    rollupOptions: {
      output: { manualChunks: undefined },
    },
  },
});
