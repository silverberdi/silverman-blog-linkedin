import type { AuthProvider } from "./auth";
import { defaultAuthProvider } from "./auth";
import {
  authMissingError,
  businessFailureError,
  forbiddenError,
  format422Detail,
  httpError,
  mutationDeniedError,
  networkError,
  unauthorizedError,
  validationError,
  type ApiError,
} from "./errors";
import {
  CANCEL_PATH,
  CORRECT_PATH,
  DEFER_PATH,
  GAP_OPERATOR_SETTINGS_PATH,
  PENDING_APPROVAL_DRAFTS_PATH,
  PENDING_SUPERVISION_PATH,
  REOPEN_PATH,
  SCHEDULE_VISIBILITY_PATH,
  UPDATE_CALENDAR_SCHEDULE_PATH,
  type CancelVariantRequest,
  type CalendarScheduleUpdateResult,
  type CorrectVariantRequest,
  type DeferVariantRequest,
  type FlowBApproveDraftRequest,
  type FlowBDraftDecisionResponse,
  type FlowBPendingDraftDetail,
  type FlowBPendingDraftListResponse,
  type FlowBRejectDraftRequest,
  type GapOperatorSettingsPutRequest,
  type GapOperatorSettingsResponse,
  type MutationResult,
  type PendingSupervisionResponse,
  type ReopenVariantRequest,
  type ScheduleVisibilityResponse,
  type UpdateCalendarItemScheduleRequest,
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

  getAuth(): AuthProvider {
    return this.auth;
  }

  canRead(): boolean {
    return this.auth.canRead();
  }

  canMutate(): boolean {
    return this.auth.canMutate();
  }

  hasCredential(): boolean {
    return this.auth.hasCredential();
  }

  async signIn(): Promise<boolean> {
    return this.auth.signIn();
  }

  async getPendingSupervision(): Promise<PendingSupervisionResponse> {
    const headers = await this.prepareHeaders("load");
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

  async getScheduleVisibility(params: {
    year: number;
    month: number;
  }): Promise<ScheduleVisibilityResponse> {
    const headers = await this.prepareHeaders("load");
    const query = new URLSearchParams({
      year: String(params.year),
      month: String(params.month),
    });
    return this.requestJson<ScheduleVisibilityResponse>(
      `${SCHEDULE_VISIBILITY_PATH}?${query.toString()}`,
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

  async reopenVariant(body: ReopenVariantRequest): Promise<MutationResult> {
    return this.postMutation(REOPEN_PATH, body);
  }

  async updateCalendarItemSchedule(
    body: UpdateCalendarItemScheduleRequest,
  ): Promise<CalendarScheduleUpdateResult> {
    const headers = await this.prepareHeaders("mutate");
    const result = await this.requestJson<CalendarScheduleUpdateResult>(
      UPDATE_CALENDAR_SCHEDULE_PATH,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify(body),
      },
    );
    if (result.status === "failed") {
      throw businessFailureError(
        Array.isArray(result.errors) ? result.errors : [],
      );
    }
    return result;
  }

  async getGapOperatorSettings(): Promise<GapOperatorSettingsResponse> {
    const headers = await this.prepareHeaders("load");
    return this.requestJson<GapOperatorSettingsResponse>(
      GAP_OPERATOR_SETTINGS_PATH,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          ...headers,
        },
      },
    );
  }

  async putGapOperatorSettings(
    body: GapOperatorSettingsPutRequest,
  ): Promise<GapOperatorSettingsResponse> {
    const headers = await this.prepareHeaders("mutate");
    return this.requestJson<GapOperatorSettingsResponse>(
      GAP_OPERATOR_SETTINGS_PATH,
      {
        method: "PUT",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify(body),
      },
    );
  }

  async listPendingApprovalDrafts(params?: {
    status?: string;
  }): Promise<FlowBPendingDraftListResponse> {
    const headers = await this.prepareHeaders("load");
    const query = new URLSearchParams();
    if (params?.status) {
      query.set("status", params.status);
    }
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return this.requestJson<FlowBPendingDraftListResponse>(
      `${PENDING_APPROVAL_DRAFTS_PATH}${suffix}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          ...headers,
        },
      },
    );
  }

  async getPendingApprovalDraft(
    draftId: string,
  ): Promise<FlowBPendingDraftDetail> {
    const headers = await this.prepareHeaders("load");
    return this.requestJson<FlowBPendingDraftDetail>(
      `${PENDING_APPROVAL_DRAFTS_PATH}/${encodeURIComponent(draftId)}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          ...headers,
        },
      },
    );
  }

  async fetchPendingApprovalDraftImage(
    draftId: string,
  ): Promise<Blob> {
    const headers = await this.prepareHeaders("load");
    const credentials = this.auth.getCredentialsMode();
    let response: Response;
    try {
      response = await this.fetchImpl(
        `${PENDING_APPROVAL_DRAFTS_PATH}/${encodeURIComponent(draftId)}/image`,
        {
          method: "GET",
          headers: {
            Accept: "image/png,image/*",
            ...headers,
          },
          credentials,
        },
      );
    } catch (err) {
      throw networkError(err instanceof Error ? err.message : String(err));
    }
    if (response.status === 401) {
      this.auth.clear();
      throw unauthorizedError();
    }
    if (response.status === 403) {
      throw forbiddenError();
    }
    if (!response.ok) {
      throw httpError(response.status);
    }
    return response.blob();
  }

  async approvePendingApprovalDraft(
    draftId: string,
    body: FlowBApproveDraftRequest = {},
  ): Promise<FlowBDraftDecisionResponse> {
    const headers = await this.prepareHeaders("mutate");
    return this.requestJson<FlowBDraftDecisionResponse>(
      `${PENDING_APPROVAL_DRAFTS_PATH}/${encodeURIComponent(draftId)}/approve`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify(body),
      },
    );
  }

  async rejectPendingApprovalDraft(
    draftId: string,
    body: FlowBRejectDraftRequest = {},
  ): Promise<FlowBDraftDecisionResponse> {
    const headers = await this.prepareHeaders("mutate");
    return this.requestJson<FlowBDraftDecisionResponse>(
      `${PENDING_APPROVAL_DRAFTS_PATH}/${encodeURIComponent(draftId)}/reject`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify(body),
      },
    );
  }

  private async prepareHeaders(
    context: "load" | "mutate",
  ): Promise<Record<string, string>> {
    const headers = await this.auth.getRequestHeaders();
    const mode = this.auth.getCredentialsMode();

    if (context === "mutate" && !this.auth.canMutate()) {
      if (this.auth.hasCredential() || this.auth.canRead()) {
        throw mutationDeniedError();
      }
      throw authMissingError("mutate");
    }

    if (context === "load" && !this.auth.canRead()) {
      throw authMissingError("load");
    }

    if (mode === "omit") {
      if (!headers.Authorization) {
        throw authMissingError(context);
      }
    }
    // Cookie mode: empty headers are expected; credentials: "include" carries the session.
    return headers;
  }

  private async postMutation(
    path: string,
    body:
      | CorrectVariantRequest
      | DeferVariantRequest
      | CancelVariantRequest
      | ReopenVariantRequest,
  ): Promise<MutationResult> {
    const headers = await this.prepareHeaders("mutate");
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
    const credentials = this.auth.getCredentialsMode();
    let response: Response;
    try {
      response = await this.fetchImpl(path, {
        ...init,
        credentials,
      });
    } catch (err) {
      throw networkError(err instanceof Error ? err.message : String(err));
    }

    if (response.status === 401) {
      this.auth.clear();
      throw unauthorizedError();
    }

    if (response.status === 403) {
      throw forbiddenError();
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
