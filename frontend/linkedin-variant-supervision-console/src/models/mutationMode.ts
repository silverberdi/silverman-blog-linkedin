/**
 * Preview vs real mutation copy (US-083) — shared across EventModal + ScheduleEditor.
 */

export const PREVIEW_CHECKBOX_LABEL =
  "Preview (no change) — validates without saving";

export const REAL_CHECKBOX_HINT =
  "Unchecked = Make real change — will save when you commit";

export function dryRunModeBanner(dryRun: boolean): string {
  return dryRun
    ? "Mode: Preview — no lasting change will be made."
    : "Mode: Make real change — this will save when you commit (not a LinkedIn live publish).";
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
