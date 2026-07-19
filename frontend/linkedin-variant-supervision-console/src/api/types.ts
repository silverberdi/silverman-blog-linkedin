/** Worker API path constants and response/request types (US-017 + pending-supervision + US-040B). */

export const PENDING_SUPERVISION_PATH =
  "/flow-a/linkedin-variants/pending-supervision";
export const SCHEDULE_VISIBILITY_PATH = "/flow-a/schedule-visibility";
export const CORRECT_PATH = "/correct-linkedin-variant";
export const DEFER_PATH = "/defer-linkedin-variant";
export const CANCEL_PATH = "/cancel-linkedin-publication";
export const REOPEN_PATH = "/reopen-linkedin-variant";
export const UPDATE_CALENDAR_SCHEDULE_PATH =
  "/editorial-calendar/update-item-schedule";

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

export type ScheduleChannel = "blog" | "linkedin";

export type PublicationDisplayState =
  | "planned"
  | "pending"
  | "queued"
  | "published"
  | "completed"
  | "deferred"
  | "cancelled"
  | "blocked"
  | "failed";

export interface ScheduleVisibilityItemDto {
  item_id: string;
  channel: ScheduleChannel | string;
  campaign_id: string | null;
  variant_id: string | null;
  title: string | null;
  audience: string | null;
  scheduled_at_utc: string | null;
  publication_state: PublicationDisplayState | string;
  source_state: string | null;
  blocked: boolean;
  critical: boolean;
  linkedin_api_published: boolean;
  calendar_item_id?: string | null;
  schedule_editable?: boolean;
  schedule_edit_block_reason?: string | null;
  /** US-040J additive cancellation context (cancelled LinkedIn items). */
  cancelled_at_utc?: string | null;
  cancellation_phase?: string | null;
  cancellation_reason?: string | null;
  reopen_eligible?: boolean | null;
}

export interface ScheduleVisibilityResponse {
  status: PendingSupervisionStatus | string;
  observed_at_utc: string;
  read_only: boolean;
  year: number;
  month: number;
  from_utc: string;
  to_utc: string;
  linkedin_publication_enabled: boolean;
  calendar_fingerprint?: string | null;
  items: ScheduleVisibilityItemDto[];
  issues: SupervisionIssueDto[];
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
  actor?: string | null;
  source?: string | null;
  /** IANA timezone for US-040K local-day density (browser resolved). */
  operator_timezone?: string | null;
}

export interface CancelVariantRequest {
  campaign_id: string;
  variant: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
}

export interface ReopenVariantRequest {
  campaign_id: string;
  variant: string;
  new_scheduled_at_utc: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
  actor?: string | null;
  source?: string | null;
  /** IANA timezone for US-040K local-day density (browser resolved). */
  operator_timezone?: string | null;
}

export interface UpdateCalendarItemScheduleRequest {
  item_id: string;
  new_due_at_utc: string;
  dry_run?: boolean;
  reason?: string | null;
  idempotency_key?: string | null;
  actor?: string | null;
  source?: string | null;
  expected_calendar_fingerprint?: string | null;
  /** IANA timezone for US-040K local-day density (browser resolved). */
  operator_timezone?: string | null;
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

export interface CalendarScheduleUpdateResult {
  status: "completed" | "failed" | string;
  dry_run: boolean;
  item_id: string | null;
  previous_due_at_utc: string | null;
  new_due_at_utc: string | null;
  calendar_path?: string;
  calendar_written: boolean;
  idempotency_result?: string | null;
  related_linkedin_variants_outcome?: string | null;
  audit?: Record<string, unknown> | null;
  errors: string[];
  warnings?: string[];
}
