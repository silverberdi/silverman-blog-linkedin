import type { AuthProvider } from "./auth";
import { defaultAuthProvider } from "./auth";
import {
  authMissingError,
  businessFailureError,
  format422Detail,
  httpError,
  networkError,
  unauthorizedError,
  validationError,
  type ApiError,
} from "./errors";
import {
  CANCEL_PATH,
  CORRECT_PATH,
  DEFER_PATH,
  PENDING_SUPERVISION_PATH,
  type CancelVariantRequest,
  type CorrectVariantRequest,
  type DeferVariantRequest,
  type MutationResult,
  type PendingSupervisionResponse,
} from "./types";

export type { ApiError };

export class SupervisionApiClient {
  constructor(
    private readonly auth: AuthProvider = defaultAuthProvider,
    private readonly fetchImpl: typeof fetch = fetch.bind(globalThis),
  ) {}

  clearAuth(): void {
    this.auth.clear();
  }

  async getPendingSupervision(): Promise<PendingSupervisionResponse> {
    const headers = await this.auth.getRequestHeaders();
    if (!headers.Authorization) {
      throw authMissingError("load");
    }
    return this.requestJson<PendingSupervisionResponse>(
      PENDING_SUPERVISION_PATH,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          ...headers,
        },
      },
    );
  }

  async correctVariant(
    body: CorrectVariantRequest,
  ): Promise<MutationResult> {
    return this.postMutation(CORRECT_PATH, body);
  }

  async deferVariant(body: DeferVariantRequest): Promise<MutationResult> {
    return this.postMutation(DEFER_PATH, body);
  }

  async cancelVariant(body: CancelVariantRequest): Promise<MutationResult> {
    return this.postMutation(CANCEL_PATH, body);
  }

  private async postMutation(
    path: string,
    body: CorrectVariantRequest | DeferVariantRequest | CancelVariantRequest,
  ): Promise<MutationResult> {
    const headers = await this.auth.getRequestHeaders();
    if (!headers.Authorization) {
      throw authMissingError("mutate");
    }
    const result = await this.requestJson<MutationResult>(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...headers,
      },
      body: JSON.stringify(body),
    });
    if (result.status === "failed") {
      throw businessFailureError(
        Array.isArray(result.errors) ? result.errors : [],
      );
    }
    return result;
  }

  private async requestJson<T>(
    path: string,
    init: RequestInit,
  ): Promise<T> {
    let response: Response;
    try {
      response = await this.fetchImpl(path, init);
    } catch (err) {
      throw networkError(err instanceof Error ? err.message : String(err));
    }

    if (response.status === 401) {
      this.auth.clear();
      throw unauthorizedError();
    }

    if (response.status === 422) {
      let body: unknown = null;
      try {
        body = await response.json();
      } catch {
        body = null;
      }
      throw validationError(format422Detail(body));
    }

    if (!response.ok) {
      throw httpError(response.status);
    }

    return (await response.json()) as T;
  }
}

export const apiClient = new SupervisionApiClient();
