/**
 * Injectable auth header / credentials provider (US-040D readiness).
 *
 * Local ops: in-memory API key via prompt only — never browser storage APIs.
 * Future: swap for OIDC bearer or secure session cookie without changing
 * list, month calendar, or schedule-editor business components.
 */

export interface AuthProvider {
  /** Return auth headers for worker API calls (e.g. Authorization: Bearer …). */
  getRequestHeaders(): Promise<Record<string, string>>;
  /**
   * Fetch credentials mode. Bearer providers use "omit"; cookie/session
   * providers use "include" with empty or minimal auth headers.
   */
  getCredentialsMode(): RequestCredentials;
  /** Clear any held credential (memory only). */
  clear(): void;
  /** True when a credential / signed-in session is currently held. */
  hasCredential(): boolean;
  /** Provider-level read capability (credential present for MemoryBearer). */
  canRead(): boolean;
  /** Provider-level mutation capability (MemoryBearer: same as canRead). */
  canMutate(): boolean;
  /**
   * Explicit sign-in / re-auth entry (prompt or future OIDC redirect).
   * Returns true when a usable credential is held afterward.
   */
  signIn(): Promise<boolean>;
}

export type PromptFn = (message: string) => string | null;

/**
 * Memory-only Bearer token provider matching worker `require_api_key` semantics.
 * Credential held ⇒ canRead and canMutate both true; none ⇒ both false.
 */
export class MemoryBearerAuthProvider implements AuthProvider {
  private token: string | null = null;

  constructor(private readonly promptFn: PromptFn = defaultPrompt) {}

  getCredentialsMode(): RequestCredentials {
    return "omit";
  }

  hasCredential(): boolean {
    return Boolean(this.token);
  }

  canRead(): boolean {
    return this.hasCredential();
  }

  canMutate(): boolean {
    return this.hasCredential();
  }

  clear(): void {
    this.token = null;
  }

  async signIn(): Promise<boolean> {
    this.token = null;
    await this.getRequestHeaders();
    return this.hasCredential();
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

/**
 * Read-only bearer provider for capability gating tests / future OIDC roles.
 * Credential held ⇒ canRead true, canMutate false.
 */
export class ReadOnlyBearerAuthProvider implements AuthProvider {
  private token: string | null = null;

  constructor(private readonly promptFn: PromptFn = defaultPrompt) {}

  getCredentialsMode(): RequestCredentials {
    return "omit";
  }

  hasCredential(): boolean {
    return Boolean(this.token);
  }

  canRead(): boolean {
    return this.hasCredential();
  }

  canMutate(): boolean {
    return false;
  }

  clear(): void {
    this.token = null;
  }

  async signIn(): Promise<boolean> {
    this.token = null;
    await this.getRequestHeaders();
    return this.hasCredential();
  }

  async getRequestHeaders(): Promise<Record<string, string>> {
    if (!this.token) {
      const entered = this.promptFn(
        "Enter your worker API key for this browser session (read-only; not stored in the page source or browser storage):",
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

  setTokenForTests(token: string | null): void {
    this.token = token;
  }
}

/**
 * Cookie / credentials-mode provider (OIDC session swap smoke).
 * Uses credentials: "include" with no Authorization header construction in
 * calendar components — only the API client reads this provider.
 */
export class CookieSessionAuthProvider implements AuthProvider {
  private signedIn = false;
  private mutable = true;

  getCredentialsMode(): RequestCredentials {
    return "include";
  }

  hasCredential(): boolean {
    return this.signedIn;
  }

  canRead(): boolean {
    return this.signedIn;
  }

  canMutate(): boolean {
    return this.signedIn && this.mutable;
  }

  clear(): void {
    this.signedIn = false;
  }

  async signIn(): Promise<boolean> {
    this.signedIn = true;
    return true;
  }

  async getRequestHeaders(): Promise<Record<string, string>> {
    // Cookie auth: no bearer header; browser sends session cookie via credentials.
    return {};
  }

  /** Test / future IdP: mark session present without calendar component changes. */
  setSignedInForTests(signedIn: boolean, mutable = true): void {
    this.signedIn = signedIn;
    this.mutable = mutable;
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
