/**
 * Preview vs real mutation copy (US-083) — shared across EventModal + ScheduleEditor.
 * Publish-now (US-086) uses dedicated banners/toasts so real mode is not mistaken
 * for “not a LinkedIn live publish.”
 */

export const PREVIEW_CHECKBOX_LABEL =
  "Preview (no change) — validates without saving";

export const PREVIEW_PUBLISH_CHECKBOX_LABEL =
  "Preview (no LinkedIn send) — validates without calling the LinkedIn API";

export const REAL_CHECKBOX_HINT =
  "Unchecked = Make real change — will save when you commit";

export function dryRunModeBanner(dryRun: boolean): string {
  return dryRun
    ? "Mode: Preview — no lasting change will be made."
    : "Mode: Make real change — this will save when you commit (not a LinkedIn live publish).";
}

/** US-086 publish-now mode banner (Preview ≠ Live; Real = LinkedIn API send). */
export function publishDryRunModeBanner(dryRun: boolean): string {
  return dryRun
    ? "Mode: Preview — no LinkedIn API send. Outcome must not be treated as Live on LinkedIn."
    : "Mode: Real publish — this will send to the LinkedIn API now when you confirm and commit.";
}

export function mutationOutcomeToast(
  action: string,
  dryRun: boolean,
  identity: string,
): string {
  const isCancel =
    action === "Cancel" || action.toLowerCase().startsWith("cancel");
  if (dryRun) {
    if (isCancel) {
      return (
        `Preview only (dry-run): ${action} validated for ${identity}. ` +
        `No lasting change was made. Not Cancelled for real. Not live on LinkedIn.`
      );
    }
    return (
      `Preview only (dry-run): ${action} validated for ${identity}. ` +
      `No lasting change was made. Not live on LinkedIn.`
    );
  }
  if (isCancel) {
    return (
      `Saved: Cancel committed for ${identity}. ` +
      `Variant is Cancelled and will not send — reopen to restore when eligible. Not live on LinkedIn.`
    );
  }
  return (
    `Saved: ${action} committed for ${identity}. ` +
    `Campaign metadata updated — not live on LinkedIn.`
  );
}

/** US-086 publish-now outcome toast — preview never claims Live; real includes URN. */
export function publishOutcomeToast(opts: {
  dryRun: boolean;
  identity: string;
  urn: string | null;
}): string {
  if (opts.dryRun) {
    return (
      `Preview only (dry-run): publish now validated for ${opts.identity}. ` +
      `No LinkedIn API send was committed. Not Live on LinkedIn.`
    );
  }
  const urnPart = opts.urn
    ? ` Publication identity (URN): ${opts.urn}.`
    : " Verify Live status after refresh if URN was not returned.";
  return (
    `Live on LinkedIn: publish now succeeded for ${opts.identity}.${urnPart}`
  );
}

export function scheduleOutcomeToast(
  dryRun: boolean,
  itemId: string,
  detail: string,
): string {
  if (dryRun) {
    return (
      `Preview only (dry-run): schedule change validated for ${itemId}. ` +
      `Schedule was not saved. Not live on LinkedIn.`
    );
  }
  return (
    `Saved: schedule committed for ${itemId}. ${detail} ` +
    `Not live on LinkedIn.`
  );
}
