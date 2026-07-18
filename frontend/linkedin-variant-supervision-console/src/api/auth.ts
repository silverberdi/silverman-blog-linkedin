/**
 * Injectable auth header provider (US-040D readiness).
 *
 * US-040A: in-memory API key via prompt only — never localStorage/sessionStorage.
 * US-040D: swap this implementation for OIDC bearer / session cookie without
 * changing list or calendar business components.
 */

export interface AuthProvider {
  /** Return auth headers for worker API calls (e.g. Authorization: Bearer …). */
  getRequestHeaders(): Promise<Record<string, string>>;
  /** Clear any held credential (memory only). */
  clear(): void;
  /** True when a credential is currently held in memory. */
  hasCredential(): boolean;
}

export type PromptFn = (message: string) => string | null;

/**
 * Memory-only Bearer token provider matching worker `require_api_key` semantics.
 */
export class MemoryBearerAuthProvider implements AuthProvider {
  private token: string | null = null;

  constructor(private readonly promptFn: PromptFn = defaultPrompt) {}

  hasCredential(): boolean {
    return Boolean(this.token);
  }

  clear(): void {
    this.token = null;
  }

  async getRequestHeaders(): Promise<Record<string, string>> {
    if (!this.token) {
      const entered = this.promptFn(
        "Enter your worker API key for this browser session (not stored in the page source or browser storage):",
      );
      if (!entered || !entered.trim()) {
        return {};
      }
      this.token = entered.trim();
    }
    return {
      Authorization: `Bearer ${this.token}`,
    };
  }

  /** Test helper: set token without prompting. */
  setTokenForTests(token: string | null): void {
    this.token = token;
  }
}

function defaultPrompt(message: string): string | null {
  if (typeof window === "undefined" || typeof window.prompt !== "function") {
    return null;
  }
  return window.prompt(message, "");
}

/** Default singleton used by the console; replaceable for OIDC later. */
export const defaultAuthProvider = new MemoryBearerAuthProvider();
