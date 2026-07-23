/**
 * Injectable auth header / credentials provider (US-040D / US-097 / US-098).
 *
 * Local ops fallback: MemoryBearerAuthProvider (API-key prompt) for tests /
 * explicit Google-disabled local use only — NOT the default when Google auth
 * is enabled.
 * Google path: GoogleOidcAuthProvider — OIDC redirect, operator JWT via
 * HttpOnly cookie (credentials: "include"), never the worker API key.
 */

export interface AuthProvider {
  /** Return auth headers for worker API calls (e.g. Authorization: Bearer …). */
  getRequestHeaders(): Promise<Record<string, string>>;
  /**
   * Fetch credentials mode. Bearer providers use "omit"; cookie/session
   * providers use "include" with empty or minimal auth headers.
   */
  getCredentialsMode(): RequestCredentials;
  /** Clear any held credential (memory only; cookie providers also logout). */
  clear(): void;
  /** True when a credential / signed-in session is currently held. */
  hasCredential(): boolean;
  /** Provider-level read capability (credential present for MemoryBearer). */
  canRead(): boolean;
  /** Provider-level mutation capability (MemoryBearer: same as canRead). */
  canMutate(): boolean;
  /**
   * Explicit sign-in / re-auth entry (prompt or Google OIDC redirect).
   * Returns true when a usable allowlisted credential is held afterward.
   * May return false when cancelled, forbidden, or redirecting away.
   */
  signIn(): Promise<boolean>;
  /**
   * US-040D / US-097 identity vocabulary hint for the store.
   * forbidden = Google identity present at IdP but not allowlisted.
   */
  getIdentityState(): "anonymous" | "authenticated" | "forbidden";
}

export type PromptFn = (message: string) => string | null;

/**
 * Memory-only Bearer token provider matching worker API-key semantics.
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

  getIdentityState(): "anonymous" | "authenticated" | "forbidden" {
    return this.hasCredential() ? "authenticated" : "anonymous";
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

  getIdentityState(): "anonymous" | "authenticated" | "forbidden" {
    return this.hasCredential() ? "authenticated" : "anonymous";
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
  private forbidden = false;

  getCredentialsMode(): RequestCredentials {
    return "include";
  }

  hasCredential(): boolean {
    return this.signedIn && !this.forbidden;
  }

  canRead(): boolean {
    return this.hasCredential();
  }

  canMutate(): boolean {
    return this.signedIn && this.mutable && !this.forbidden;
  }

  getIdentityState(): "anonymous" | "authenticated" | "forbidden" {
    if (this.forbidden) {
      return "forbidden";
    }
    return this.signedIn ? "authenticated" : "anonymous";
  }

  clear(): void {
    this.signedIn = false;
    this.forbidden = false;
  }

  async signIn(): Promise<boolean> {
    this.forbidden = false;
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
    this.forbidden = false;
  }

  /** Test helper: non-allowlisted deny state. */
  setForbiddenForTests(forbidden: boolean): void {
    this.forbidden = forbidden;
    if (forbidden) {
      this.signedIn = false;
    }
  }
}

export type FetchLike = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export type NavigateFn = (url: string) => void;

/**
 * Google OIDC AuthProvider for the separated UI (US-097 / US-098).
 * Sign-in redirects to worker `/auth/google/start` — no worker API-key paste.
 * Console→API uses HttpOnly operator JWT cookie via credentials: "include"
 * and never puts the worker API key in Authorization headers.
 */
export class GoogleOidcAuthProvider implements AuthProvider {
  private identity: "anonymous" | "authenticated" | "forbidden" = "anonymous";
  private email: string | null = null;
  private configError: string | null = null;

  constructor(
    private readonly apiBaseUrl: string,
    private readonly fetchFn: FetchLike = fetch.bind(globalThis),
    private readonly navigate: NavigateFn = (url) => {
      window.location.assign(url);
    },
  ) {}

  getCredentialsMode(): RequestCredentials {
    return "include";
  }

  hasCredential(): boolean {
    return this.identity === "authenticated";
  }

  canRead(): boolean {
    return this.hasCredential();
  }

  canMutate(): boolean {
    return this.identity === "authenticated";
  }

  getIdentityState(): "anonymous" | "authenticated" | "forbidden" {
    return this.identity;
  }

  getConfigError(): string | null {
    return this.configError;
  }

  getEmail(): string | null {
    return this.email;
  }

  clear(): void {
    this.identity = "anonymous";
    this.email = null;
    void this.fetchFn(joinAuthUrl(this.apiBaseUrl, "/auth/logout"), {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    }).catch(() => {
      // Best-effort logout; local state already cleared.
    });
  }

  /**
   * Restore session from URL auth outcome + /auth/me.
   * Call once at bootstrap before rendering the console.
   */
  async restoreSession(
    search: string = typeof window !== "undefined" ? window.location.search : "",
  ): Promise<"anonymous" | "authenticated" | "forbidden"> {
    const params = new URLSearchParams(
      search.startsWith("?") ? search.slice(1) : search,
    );
    const authOutcome = params.get("auth");
    if (authOutcome === "forbidden") {
      this.identity = "forbidden";
      this.email = null;
      this.stripAuthQuery();
      return "forbidden";
    }
    if (authOutcome === "error") {
      this.identity = "anonymous";
      this.email = null;
      this.stripAuthQuery();
      return "anonymous";
    }
    if (authOutcome === "ok") {
      this.stripAuthQuery();
    }

    try {
      const statusRes = await this.fetchFn(
        joinAuthUrl(this.apiBaseUrl, "/auth/google/status"),
        { method: "GET", credentials: "include", headers: { Accept: "application/json" } },
      );
      if (statusRes.ok) {
        const status = (await statusRes.json()) as {
          enabled?: boolean;
          configured?: boolean;
        };
        if (status.enabled && !status.configured) {
          this.configError =
            "Google operator authentication is enabled but not fully configured " +
            "on the worker. Required env vars are missing or invalid (fail closed).";
          this.identity = "anonymous";
          return "anonymous";
        }
      }
    } catch {
      // Status probe is best-effort; /auth/me still decides session.
    }

    try {
      const meRes = await this.fetchFn(joinAuthUrl(this.apiBaseUrl, "/auth/me"), {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!meRes.ok) {
        this.identity = "anonymous";
        this.email = null;
        return "anonymous";
      }
      const me = (await meRes.json()) as {
        authenticated?: boolean;
        email?: string | null;
      };
      if (me.authenticated && typeof me.email === "string") {
        this.identity = "authenticated";
        this.email = me.email;
        return "authenticated";
      }
    } catch {
      this.identity = "anonymous";
      this.email = null;
      return "anonymous";
    }

    this.identity = "anonymous";
    this.email = null;
    return "anonymous";
  }

  async signIn(): Promise<boolean> {
    // No API-key prompt — navigate to worker OIDC start.
    this.configError = null;
    this.navigate(joinAuthUrl(this.apiBaseUrl, "/auth/google/start"));
    return false;
  }

  async getRequestHeaders(): Promise<Record<string, string>> {
    // US-098: operator JWT is HttpOnly cookie only — never Authorization API key.
    return {};
  }

  /** Test helper: set identity without redirect. */
  setIdentityForTests(
    identity: "anonymous" | "authenticated" | "forbidden",
    email: string | null = null,
  ): void {
    this.identity = identity;
    this.email = email;
  }

  private stripAuthQuery(): void {
    if (typeof window === "undefined" || !window.history?.replaceState) {
      return;
    }
    const url = new URL(window.location.href);
    if (!url.searchParams.has("auth")) {
      return;
    }
    url.searchParams.delete("auth");
    const next = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, "", next);
  }
}

function joinAuthUrl(apiBaseUrl: string, path: string): string {
  // Same-origin private hop (US-099): empty base → root-relative auth paths.
  if (!apiBaseUrl) {
    return path.startsWith("/") ? path : `/${path}`;
  }
  const base = apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
  return new URL(path.replace(/^\//, ""), base).toString();
}

function defaultPrompt(message: string): string | null {
  if (typeof window === "undefined" || typeof window.prompt !== "function") {
    return null;
  }
  return window.prompt(message, "");
}

/** Default singleton used when Google auth is not enabled (tests / local fallback). */
export const defaultAuthProvider = new MemoryBearerAuthProvider();

/** Choose AuthProvider for separated UI bootstrap (US-097 / US-098).
 * Google enabled → GoogleOidcAuthProvider (JWT cookie). MemoryBearer is
 * Google-disabled local / test fallback only.
 */
export function createAuthProviderForConfig(options: {
  googleAuthEnabled: boolean;
  apiBaseUrl: string;
  fetchFn?: FetchLike;
}): AuthProvider {
  if (options.googleAuthEnabled) {
    return new GoogleOidcAuthProvider(
      options.apiBaseUrl,
      options.fetchFn ?? fetch.bind(globalThis),
    );
  }
  return defaultAuthProvider;
}
