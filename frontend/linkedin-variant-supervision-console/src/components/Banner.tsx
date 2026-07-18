import type { BannerKind } from "../models/store";

export function Banner({
  kind,
  text,
  testId,
}: {
  kind: BannerKind;
  text: string;
  testId?: string;
}) {
  if (!text) {
    return null;
  }
  return (
    <div
      className={`banner ${kind || "info"}`}
      data-testid={testId}
      role="status"
    >
      {text}
    </div>
  );
}
