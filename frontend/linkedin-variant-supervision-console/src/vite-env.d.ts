/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Historical; ignored after US-096 (separated delivery only). */
  readonly VITE_OPERATOR_UI_DELIVERY?: string;
  readonly VITE_WORKER_PROXY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
