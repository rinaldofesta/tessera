import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { Report } from "@/types";
import { Scorecard } from "./Scorecard";

afterEach(cleanup);

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
    { key: "none", n_probes: 2, pass_k_rate: 1, mean_rate: 1, flaky: false },
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
          question: "which policy wins?",
          answer: "policy A wins",
          consulted: ["wiki"],
          expected_sources: ["policy"],
          missing: ["policy"],
          answer_format_ok: null,
        },
      ],
    },
  ],
};

describe("Scorecard", () => {
  it("shows the not-reliable verdict naming the failing category", () => {
    render(<Scorecard report={report} />);
    expect(screen.getByText(/Not reliable on genuine disagreement/)).toBeInTheDocument();
  });

  it("renders one gap bar per category with the aria sentence", () => {
    render(<Scorecard report={report} />);
    const bars = screen.getAllByRole("img");
    expect(bars).toHaveLength(2);
    expect(bars[0]).toHaveAttribute(
      "aria-label",
      "50% reliable (pass^3), 75% mean success, 25 point gap",
    );
  });

  it("badges categories with reliability verdicts, not lifecycle", () => {
    render(<Scorecard report={report} />);
    // "inconsistent" appears on the category row AND on the open failure header — assert presence, not uniqueness
    expect(screen.getAllByText("inconsistent").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("reliable")).toBeInTheDocument();
  });

  it("expands a failure to show the answer and the missing sources", async () => {
    render(<Scorecard report={report} />);
    // the first failing probe starts open (existing behavior); collapse–reopen exercises the toggle
    expect(screen.getByText(/"policy A wins"/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /p1/ }));
    expect(screen.queryByText(/"policy A wins"/)).not.toBeInTheDocument();
  });

  it("explains a refuse-probe failure in behavior terms", () => {
    render(<Scorecard report={report} />);
    expect(
      screen.getByText(/repeat 2 — committed to an answer when it should have refused/),
    ).toBeInTheDocument();
  });
});
