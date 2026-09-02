import { describe, expect, it } from "vitest";
import { runFixture } from "@/test/fixtures";
import { summaryText } from "./summaryText";

describe("summaryText", () => {
  it("is exactly three lines", () => {
    expect(summaryText(runFixture())).toBe([
      "Not reliable. Right every time on 1 of 2 questions.",
      "pass^3 50% · mean 75% · starter · anthropic/claude-sonnet-4 · 3 repeats",
      "tessera report run-1",
    ].join("\n"));
  });
});
