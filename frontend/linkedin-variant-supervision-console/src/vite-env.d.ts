/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OPERATOR_UI_DELIVERY?: "separated" | "embedded";
  readonly VITE_WORKER_PROXY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
