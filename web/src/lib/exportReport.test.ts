import { describe, expect, it } from "vitest";
import { reportFixture, runFixture } from "@/test/fixtures";
import { exportReportHtml, reportFilename } from "./exportReport";

const ATTACK = `<script>alert(1)</script> " ' &`;
const report = {
  ...reportFixture,
  header: { ...reportFixture.header, model: ATTACK, org: ATTACK, created: ATTACK, location: ATTACK },
  categories: [{ ...reportFixture.categories[0], key: ATTACK }],
  probes: [{ ...reportFixture.probes[0], probe_id: ATTACK, conflict_type: ATTACK, failures: [{ ...reportFixture.probes[0].failures[0], question: ATTACK, answer: ATTACK, consulted: [ATTACK], expected_sources: [ATTACK], missing: [ATTACK] }] }],
};
const receipt = runFixture().receipt!;
const run = runFixture({
  id: ATTACK, created_at: ATTACK, report,
  request: { ...runFixture().request, model: ATTACK, suite: ATTACK },
  verdict: { ...runFixture().verdict!, sentence: ATTACK },
  diagnostics: [{ kind: ATTACK, signature: ATTACK, count: 1 }], paths: { ...runFixture().paths, log: ATTACK },
  receipt: { ...receipt, protocol_hash: ATTACK, artifact: { ...receipt.artifact, path: ATTACK }, runtime: { ...receipt.runtime, requested_model: ATTACK } },
});

describe("exportReportHtml", () => {
  const html = exportReportHtml(run);
  it("escapes every run-derived string", () => {
    expect(html).not.toContain(ATTACK);
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt; &quot; &#39; &amp;");
  });
  it("is standalone and offline", () => {
    expect(html).toContain("<!doctype html>");
    expect(html).not.toMatch(/(href|src)\s*=\s*["']https?:|@import|url\(\s*["']?https?:/i);
    expect(html).toContain("system-ui");
  });
});

describe("reportFilename", () => {
  it("keeps the safe suite-model-date shape", () => {
    expect(reportFilename(reportFixture, "html")).toBe("tessera-starter-claude-sonnet-4-2026-09-02.html");
  });
});
