import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { render } from "@testing-library/react";
import App from "../App";

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Desktop + mobile viewport validation evidence for the list-oriented console.
 * Asserts CSS media rules exist and the shell renders at both widths.
 */
describe("viewport validation", () => {
  const cssPath = resolve(__dirname, "../styles/console.css");
  const css = readFileSync(cssPath, "utf-8");

  it("includes a mobile max-width media query for the list console", () => {
    expect(css).toMatch(/@media\s*\(max-width:\s*720px\)/);
    expect(css).toMatch(/main\.console-shell/);
    expect(css).toMatch(/\.table-wrap/);
  });

  it("renders list-oriented shell at desktop viewport width", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });
    const { getByTestId, unmount } = render(<App />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("list-view")).toBeInTheDocument();
    expect(getByTestId("view-list")).toBeInTheDocument();
    unmount();
  });

  it("renders list-oriented shell at mobile viewport width", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 375,
    });
    const { getByTestId, unmount } = render(<App />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("list-view")).toBeInTheDocument();
    expect(getByTestId("load-btn")).toBeInTheDocument();
    unmount();
  });
});
