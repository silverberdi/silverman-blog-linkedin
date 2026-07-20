/** Worker API path constants and response/request types (US-017 + pending-supervision + US-040B). */

export const PENDING_SUPERVISION_PATH =
  "/flow-a/linkedin-variants/pending-supervision";
export const SCHEDULE_VISIBILITY_PATH = "/flow-a/schedule-visibility";
export const CORRECT_PATH = "/correct-linkedin-variant";
export const DEFER_PATH = "/defer-linkedin-variant";
export const CANCEL_PATH = "/cancel-linkedin-publication";
export const REOPEN_PATH = "/reopen-linkedin-variant";
export const PUBLISH_DUE_PATH = "/publish-linkedin-due-variants";
export const UPDATE_CALENDAR_SCHEDULE_PATH =
  "/editorial-calendar/update-item-schedule";
export const GAP_OPERATOR_SETTINGS_PATH = "/flow-b/gap-operator-settings";
export const PENDING_APPROVAL_DRAFTS_PATH = "/flow-b/pending-approval-drafts";

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
  /** US-086 optional Live publication identity (non-credential). */
  linkedin_post_urn?: string | null;
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

/** US-086 deliberate publish now via existing publish-due endpoint. */
export interface PublishDueVariantRequest {
  campaign_id: string;
  variant: string;
  dry_run?: boolean;
  publish_now: true;
  auto_queue_pending?: boolean;
}

export interface PublishDueVariantResultItem {
  campaign_id: string;
  variant: string;
  publish_state: string;
  publish_after_utc?: string | null;
  published_at?: string | null;
  linkedin_post_urn?: string | null;
  status: string;
  errors?: string[];
  warnings?: string[];
  skipped?: boolean;
  skip_reason?: string | null;
}

export interface PublishDueAutoQueueResultItem {
  campaign_id: string;
  variant: string;
  publish_state: string;
  publish_after_utc?: string | null;
  linkedin_post_urn?: string | null;
  published_at?: string | null;
  status: string;
  errors?: string[];
  warnings?: string[];
  skipped?: boolean;
  skip_reason?: string | null;
  metadata_written?: boolean;
}

export interface PublishDueVariantResult {
  status: "completed" | "failed" | string;
  dry_run: boolean;
  publish_now: boolean;
  results: PublishDueVariantResultItem[];
  errors: string[];
  warnings: string[];
  auto_queue_pending?: boolean;
  auto_queue_results?: PublishDueAutoQueueResultItem[];
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

/** US-076 Flow B gap operator settings. */
export type GapScanMode = "next_week";

export type WeeklyRunLocalDay =
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday"
  | "sunday";

export interface GapOperatorSettingsDocument {
  operator_timezone: string;
  gap_trigger_enabled: boolean;
  gap_scan_mode: GapScanMode | string;
  weekly_run_local_day: WeeklyRunLocalDay | string;
  weekly_run_local_time: string;
  min_lead_days: number;
  gap_posts_threshold: number;
  max_drafts_per_weekly_run: number;
  density_max_per_local_day: number;
}

export interface GapOperatorSettingsResponse extends GapOperatorSettingsDocument {
  settings_id: string;
  source: "defaults" | "database" | string;
  updated_at_utc: string | null;
  row_version: number | null;
}

export interface GapOperatorSettingsPutRequest extends GapOperatorSettingsDocument {
  expected_row_version?: number | null;
}

/** US-080 Flow B pending-approval draft presentation. */
export type FlowBDraftStatus =
  | "pending_approval"
  | "pending_approval_image_failed"
  | "approved"
  | "promoted"
  | "rejected"
  | string;

export interface FlowBPendingDraftSummary {
  draft_id: string;
  slug: string;
  title: string;
  topic_id: string | null;
  thesis: string | null;
  referent_positioning: string | null;
  rationale: string | null;
  status: FlowBDraftStatus;
  blog_relative_path: string | null;
  image_relative_path: string | null;
  metadata_relative_path: string | null;
  image_url: string | null;
  generated_at_utc: string | null;
  target_week?: string | null;
  empty_days?: string[] | null;
  image_status?: string | null;
  image_warning?: string | null;
}

export interface FlowBPendingDraftDetail extends FlowBPendingDraftSummary {
  body_markdown: string;
  approved_at_utc?: string | null;
  approved_by?: string | null;
  rejected_at_utc?: string | null;
  rejection_reason?: string | null;
}

export interface FlowBPendingDraftListResponse {
  status: "ok" | string;
  drafts: FlowBPendingDraftSummary[];
  observed_at_utc: string;
  filter_status: string | null;
  count: number;
}

export interface FlowBApproveDraftRequest {
  approved_by?: string | null;
  dry_run?: boolean;
}

export interface FlowBRejectDraftRequest {
  rejection_reason?: string | null;
  dry_run?: boolean;
}

export interface FlowBPromoteDraftRequest {
  promoted_by?: string | null;
  dry_run?: boolean;
}

export interface FlowBDraftDecisionResponse {
  status: FlowBDraftStatus | "failed" | string;
  draft_id: string;
  promoted: boolean;
  promotion_pending: boolean;
  dry_run: boolean;
  blog_relative_path?: string | null;
  image_relative_path?: string | null;
  metadata_relative_path?: string | null;
  approved_at_utc?: string | null;
  approved_by?: string | null;
  rejected_at_utc?: string | null;
  rejection_reason?: string | null;
  image_warning?: string | null;
  operator_note?: string | null;
  error_code?: string | null;
  error?: string | null;
}

export interface FlowBPromoteDraftResponse {
  status: "promoted" | "failed" | string;
  draft_id: string;
  promoted: boolean;
  promotion_pending: boolean;
  already_promoted: boolean;
  dry_run: boolean;
  blog_relative_path?: string | null;
  image_relative_path?: string | null;
  metadata_relative_path?: string | null;
  approved_at_utc?: string | null;
  approved_by?: string | null;
  promoted_at_utc?: string | null;
  promoted_by?: string | null;
  origin?: string | null;
  target_week?: string | null;
  empty_days?: string[] | null;
  flow_a_eligible: boolean;
  operator_note?: string | null;
  error_code?: string | null;
  error?: string | null;
}
