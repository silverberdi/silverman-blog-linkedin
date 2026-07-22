/// <reference types="vitest/config" />
import { defineConfig, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Delivery modes (US-093):
 * - separated (default `build`): SPA base `/` → UI image dist/
 * - embedded (`build:embedded`): worker-served path under FastAPI static/
 */
const EMBEDDED_BASE = "/flow-a/console/linkedin-variant-supervision/";
const delivery =
  process.env.VITE_OPERATOR_UI_DELIVERY === "embedded" ? "embedded" : "separated";
const isEmbedded = delivery === "embedded";

const proxyTarget = process.env.VITE_WORKER_PROXY || "http://192.168.0.194:8010";

const sharedProxy = {
  "/flow-a/linkedin-variants": { target: proxyTarget, changeOrigin: true },
  "/flow-a/schedule-visibility": { target: proxyTarget, changeOrigin: true },
  "/correct-linkedin-variant": { target: proxyTarget, changeOrigin: true },
  "/defer-linkedin-variant": { target: proxyTarget, changeOrigin: true },
  "/cancel-linkedin-publication": { target: proxyTarget, changeOrigin: true },
  "/publish-linkedin-due-variants": { target: proxyTarget, changeOrigin: true },
  "/reopen-linkedin-variant": { target: proxyTarget, changeOrigin: true },
  "/editorial-calendar": { target: proxyTarget, changeOrigin: true },
  "/editorial": { target: proxyTarget, changeOrigin: true },
  "/flow-b": { target: proxyTarget, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  base: isEmbedded ? EMBEDDED_BASE : "/",
  // Prefer process env (npm scripts / Vitest test.env) over define baking.
  server: {
    // Local UX preview: SPA on Vite, APIs proxied to the LAN worker.
    proxy: sharedProxy,
  },
  build: {
    outDir: isEmbedded
      ? path.resolve(
          __dirname,
          "../../src/silverman_blog_linkedin/static/linkedin-variant-supervision-console",
        )
      : path.resolve(__dirname, "dist"),
    emptyOutDir: true,
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    globals: true,
    // Vitest runs against embedded-compatible relative client by default.
    env: {
      VITE_OPERATOR_UI_DELIVERY: "embedded",
    },
  },
} satisfies UserConfig);
