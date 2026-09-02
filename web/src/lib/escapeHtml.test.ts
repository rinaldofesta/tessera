import { describe, expect, it } from "vitest";
import { escapeHtml } from "./escapeHtml";

describe("escapeHtml", () => {
  it("escapes the five HTML metacharacters", () => {
    expect(escapeHtml(`<a title="x" data-y='z'>&`)).toBe("&lt;a title=&quot;x&quot; data-y=&#39;z&#39;&gt;&amp;");
  });
});
