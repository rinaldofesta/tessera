import { describe, expect, it } from "vitest";
import type { Report } from "@/types";
import { esc, exportReportHtml, exportReportJson, reportFilename } from "./exportReport";

const XSS = '<script>alert("pwn")</script>';

const report: Report = {
  header: {
    model: "anthropic/claude-sonnet-4",
    engine: "llm",
    grader: "openai/gpt-5.2",
    org: "meridian",
    k: 3,
    created: "2026-08-29T14:02:11Z",
    location: "logs/x.eval",
    scorer_version: "det-4",
    inspect_ai_version: null,
    scaffold: "baseline",
    seed: 0,
    harness: "single",
  },
  overall: { pass_k_rate: 0.5, mean_rate: 0.75 },
  categories: [
    { key: "unresolvable", n_probes: 2, pass_k_rate: 0.5, mean_rate: 0.75, flaky: true },
  ],
  axes: {
    accuracy_rate: 0.8,
    provenance_rate: 0.9,
    refusal_rate: 0.5,
    n_answer_epochs: 4,
    n_refuse_epochs: 2,
    n_total_epochs: 6,
    answer_format_rate: null,
  },
  probes: [
    {
      probe_id: "p1",
      conflict_type: "unresolvable",
      expected_behavior: "refuse",
      epochs_total: 3,
      epochs_passed: 1,
      pass_k: false,
      mean_pass: 0.33,
      failures: [
        {
          epoch: 2,
          passed: false,
          accuracy_ok: true,
          provenance_ok: true,
          refusal_ok: false,
          question: `what is the ${XSS} rate?`,
          answer: `the rate is ${XSS}`,
          consulted: [`wiki/${XSS}`],
          expected_sources: ["policy"],
          missing: ["policy"],
          answer_format_ok: null,
        },
      ],
    },
  ],
};

describe("esc", () => {
  it("escapes the five HTML metacharacters", () => {
    expect(esc(`<a href="x" title='y'>&`)).toBe(
      "&lt;a href=&quot;x&quot; title=&#39;y&#39;&gt;&amp;",
    );
  });
});

describe("exportReportHtml", () => {
  const html = exportReportHtml(report);

  it("contains no script tags at all, even from report strings", () => {
    expect(html.toLowerCase()).not.toContain("<script");
    expect(html).toContain("&lt;script&gt;");
  });

  it("is a self-contained document with the run identity", () => {
    expect(html).toContain("<!doctype html>");
    expect(html).toContain("claude-sonnet-4");
    expect(html).toContain("meridian");
    expect(html).toContain("pass^3");
  });

  it("renders every failure behind a native details element", () => {
    expect(html).toContain("<details");
    expect(html).toContain("repeat 2");
  });
});

describe("exportReportJson", () => {
  it("round-trips the report", () => {
    expect(JSON.parse(exportReportJson(report))).toEqual(report);
  });
});

describe("reportFilename", () => {
  it("builds a safe, dated name from org and model", () => {
    expect(reportFilename(report, "html")).toBe("tessera-meridian-claude-sonnet-4-2026-08-29.html");
  });
  it("sanitizes characters that don't belong in filenames", () => {
    const weird = { ...report, header: { ...report.header, model: "a b/c:d" } };
    expect(reportFilename(weird, "json")).toBe("tessera-meridian-c-d-2026-08-29.json");
  });
});
