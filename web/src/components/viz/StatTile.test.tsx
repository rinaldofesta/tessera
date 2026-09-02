import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { StatTile } from "./StatTile";

afterEach(cleanup);

describe("StatTile", () => {
  it("renders label, value, and sub", () => {
    render(<StatTile label="latest reliability" value="72%" sub="pass^5" />);
    expect(screen.getByText("latest reliability")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("pass^5")).toBeInTheDocument();
  });

  it("omits the sub line when not given", () => {
    const { container } = render(<StatTile label="runs" value="12" />);
    expect(container.firstElementChild!.children).toHaveLength(2);
  });
});
