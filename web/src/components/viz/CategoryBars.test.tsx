import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CategoryBars } from "./CategoryBars";

afterEach(cleanup);

const groups = [
  {
    key: "unresolvable",
    label: "genuine disagreement",
    series: [
      { id: "run:a", label: "claude-sonnet-4", color: "#8b93ff", value: 0.5 },
      { id: "run:b", label: "gpt-5.2", color: "#4ade80", value: 1 },
      { id: "run:c", label: "qwen", color: "#fbbf24", value: null },
    ],
  },
];

describe("CategoryBars", () => {
  it("renders one bar per series with proportional width and color", () => {
    const { container } = render(<CategoryBars groups={groups} />);
    const bars = container.querySelectorAll<HTMLElement>("[data-bar]");
    expect(bars).toHaveLength(2);
    expect(bars[0].style.width).toBe("50%");
    expect(bars[0].style.background).toBeTruthy();
    expect(bars[1].style.width).toBe("100%");
  });

  it("labels the group for assistive tech", () => {
    render(<CategoryBars groups={groups} />);
    expect(screen.getByRole("img")).toHaveAttribute(
      "aria-label",
      "genuine disagreement: claude-sonnet-4 50%, gpt-5.2 100%, qwen —",
    );
  });
});
