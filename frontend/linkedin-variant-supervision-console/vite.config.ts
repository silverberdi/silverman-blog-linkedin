/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Production assets are served by the Python worker at:
 *   GET /flow-a/console/linkedin-variant-supervision
 *   GET /flow-a/console/linkedin-variant-supervision/assets/*
 */
const CONSOLE_BASE = "/flow-a/console/linkedin-variant-supervision/";

export default defineConfig({
  plugins: [react()],
  base: CONSOLE_BASE,
  server: {
    // Local UX preview: SPA on Vite, APIs proxied to the LAN worker (same relative paths).
    proxy: {
      "/flow-a/linkedin-variants": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/flow-a/schedule-visibility": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/correct-linkedin-variant": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/defer-linkedin-variant": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/cancel-linkedin-publication": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/publish-linkedin-due-variants": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/reopen-linkedin-variant": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/editorial-calendar": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/editorial": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
      "/flow-b": {
        target: process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(
      __dirname,
      "../../src/silverman_blog_linkedin/static/linkedin-variant-supervision-console",
    ),
    emptyOutDir: true,
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    globals: true,
  },
});
