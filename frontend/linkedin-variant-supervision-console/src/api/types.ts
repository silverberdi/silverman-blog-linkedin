/** Worker API path constants and response/request types (US-017 + pending-supervision). */

export const PENDING_SUPERVISION_PATH =
  "/flow-a/linkedin-variants/pending-supervision";
export const CORRECT_PATH = "/correct-linkedin-variant";
export const DEFER_PATH = "/defer-linkedin-variant";
export const CANCEL_PATH = "/cancel-linkedin-publication";

export type PendingSupervisionStatus = "ok" | "partial";

export interface PendingSupervisionVariantDto {
  campaign_id: string;
  variant_id: string;
  audience: string | null;
  scheduled_at_utc: string | null;
  publish_state: string;
  calendar_item_id: string | null;
  calendar_title: string | null;
  calendar_due_at_utc: string | null;
  calendar_status: string | null;
  operator_supervision_last_action: string | null;
  auto_queue_eligible: boolean | null;
  operator_supervision_reason: string | null;
  draft_content: string | null;
}

export interface SupervisionIssueDto {
  source: string;
  identifier: string | null;
  reason: string;
}

export interface IntegrationFailureDto {
  campaign_id: string;
  variant_id: string;
  publish_state: string;
  last_error_code?: string | null;
  http_status?: number | null;
}

export interface PendingSupervisionResponse {
  status: PendingSupervisionStatus | string;
  observed_at_utc: string;
  read_only: boolean;
  linkedin_publication_enabled: boolean;
  variants: PendingSupervisionVariantDto[];
  issues: SupervisionIssueDto[];
  integration_failures: IntegrationFailureDto[];
}

export interface CorrectVariantRequest {
  campaign_id: string;
  variant: string;
  draft_content: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
}

export interface DeferVariantRequest {
  campaign_id: string;
  variant: string;
  new_scheduled_at_utc: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
}

export interface CancelVariantRequest {
  campaign_id: string;
  variant: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
}

export interface MutationResult {
  status: "completed" | "failed" | string;
  campaign_id: string | null;
  variant: string | null;
  state: string | null;
  publish_state: string | null;
  dry_run: boolean;
  phase: string | null;
  scheduled_at_utc?: string | null;
  errors: string[];
  warnings: string[];
  metadata_written: boolean;
  artifact_written?: boolean;
  operator_supervision?: Record<string, unknown> | null;
  recovery_classification?: string | null;
}
