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
