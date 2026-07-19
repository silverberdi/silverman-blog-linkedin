import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider, ReadOnlyBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";

const DEFAULT_SETTINGS = {
  settings_id: "default",
  source: "defaults",
  updated_at_utc: null,
  row_version: null,
  operator_timezone: "America/Chicago",
  gap_trigger_enabled: false,
  gap_scan_mode: "next_week",
  weekly_run_local_day: "friday",
  weekly_run_local_time: "15:00",
  min_lead_days: 5,
  gap_posts_threshold: 0,
  max_drafts_per_weekly_run: 2,
  density_max_per_local_day: 2,
};

function basePending() {
  return {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: false,
    variants: [],
    issues: [],
    integration_failures: [],
  };
}

function baseSchedule() {
  return {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    year: 2026,
    month: 7,
    from_utc: "2026-07-01T00:00:00Z",
    to_utc: "2026-07-31T23:59:59Z",
    linkedin_publication_enabled: false,
    items: [],
    issues: [],
  };
}

function createAppClient(options?: {
  readonly?: boolean;
  settingsGet?: () => Response;
  settingsPut?: (body: unknown) => Response;
}) {
  const auth = options?.readonly
    ? new ReadOnlyBearerAuthProvider()
    : new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");

  let saved = { ...DEFAULT_SETTINGS };

  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/flow-a/linkedin-variants/pending-supervision")) {
      return new Response(JSON.stringify(basePending()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-a/schedule-visibility")) {
      return new Response(JSON.stringify(baseSchedule()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-b/gap-operator-settings")) {
      const method = (init?.method || "GET").toUpperCase();
      if (method === "GET") {
        if (options?.settingsGet) {
          return options.settingsGet();
        }
        return new Response(JSON.stringify(saved), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (method === "PUT") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (options?.settingsPut) {
          return options.settingsPut(body);
        }
        saved = {
          ...saved,
          ...body,
          source: "database",
          updated_at_utc: "2026-07-19T20:00:00Z",
          row_version: (saved.row_version ?? 0) + 1,
          expected_row_version: undefined,
        };
        delete (saved as { expected_row_version?: unknown }).expected_row_version;
        return new Response(JSON.stringify(saved), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
  });

  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

describe("US-076 Gap settings modal", () => {
  it("loads defaults and saves valid settings", async () => {
    const user = userEvent.setup();
    const client = createAppClient();
    render(<App client={client} />);

    await waitFor(() => {
      expect(screen.getByTestId("header-gap-settings-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("header-gap-settings-btn"));

    const modal = await screen.findByTestId("gap-settings-modal");
    expect(
      within(modal).getByTestId("gap-settings-publish-warning"),
    ).toHaveTextContent(/does not publish to LinkedIn/i);
    expect(within(modal).getByTestId("gap-settings-meta")).toHaveTextContent(
      /Source: defaults/i,
    );
    expect(within(modal).getByTestId("gap-settings-timezone")).toHaveValue(
      "America/Chicago",
    );

    await user.clear(within(modal).getByTestId("gap-settings-max-drafts"));
    await user.type(within(modal).getByTestId("gap-settings-max-drafts"), "1");
    await user.click(within(modal).getByTestId("gap-settings-save"));

    await waitFor(() => {
      expect(within(modal).getByTestId("gap-settings-meta")).toHaveTextContent(
        /Source: database/i,
      );
    });
    expect(within(modal).getByTestId("gap-settings-max-drafts")).toHaveValue(1);
  });

  it("shows validation errors from the worker", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      settingsPut: () =>
        new Response(
          JSON.stringify({
            detail: {
              errors: [
                {
                  field: "operator_timezone",
                  code: "operator_timezone_invalid",
                  message: "operator_timezone must be a valid IANA timezone",
                },
              ],
            },
          }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
    });
    render(<App client={client} />);

    await user.click(await screen.findByTestId("header-gap-settings-btn"));
    const modal = await screen.findByTestId("gap-settings-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("gap-settings-form")).toBeInTheDocument();
    });

    await user.clear(within(modal).getByTestId("gap-settings-timezone"));
    await user.type(
      within(modal).getByTestId("gap-settings-timezone"),
      "Not/AZone",
    );
    await user.click(within(modal).getByTestId("gap-settings-save"));

    await waitFor(() => {
      expect(within(modal).getByTestId("gap-settings-error")).toHaveTextContent(
        /valid IANA timezone/i,
      );
    });
  });

  it("blocks mutation when session cannot mutate", async () => {
    const user = userEvent.setup();
    const client = createAppClient({ readonly: true });
    render(<App client={client} />);

    await user.click(await screen.findByTestId("header-gap-settings-btn"));
    const modal = await screen.findByTestId("gap-settings-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("gap-settings-form")).toBeInTheDocument();
    });
    expect(within(modal).getByTestId("gap-settings-save")).toBeDisabled();
  });
});
