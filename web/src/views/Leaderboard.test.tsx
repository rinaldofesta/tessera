import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api";
import type { LeaderboardManifest } from "@/types";
import Leaderboard from "./Leaderboard";

vi.mock("@/api", () => ({ api: { leaderboard: vi.fn() } }));

afterEach(cleanup);

const manifest = (overrides: Partial<LeaderboardManifest> = {}): LeaderboardManifest => ({
  title: null,
  exhibitions: [],
  rows: [
    { label: "Lower", model: "openai/lower", date: "2026-08-20", pass_k_rate: 0.5, mean_rate: 0.9, categories: { none: 0.8 }, k: 5, scaffold: "baseline", seed: 0 },
    { label: "Higher", model: "anthropic/higher", date: "2026-08-21", pass_k_rate: 0.8, mean_rate: 0.85, categories: { resolvable: 0.75, void: 1 }, k: 3, scaffold: "refusal_aware", seed: 42 },
  ],
  ...overrides,
});

describe("Leaderboard", () => {
  it("ranks rows by pass^k instead of manifest order", async () => {
    vi.mocked(api.leaderboard).mockResolvedValue(manifest());
    const { container } = render(<Leaderboard />);
    await waitFor(() => expect(screen.getByText("higher")).toBeInTheDocument());
    expect(container.textContent!.indexOf("higher")).toBeLessThan(container.textContent!.indexOf("lower"));
  });

  it("renders category chips with conflict labels and percentages", async () => {
    vi.mocked(api.leaderboard).mockResolvedValue(manifest());
    render(<Leaderboard />);
    expect(await screen.findByText("conflict, tiebreaker applies 75%")).toBeInTheDocument();
    expect(screen.getByText("fact missing 100%")).toBeInTheDocument();
  });

  it("renders seed zero and a non-single harness", async () => {
    vi.mocked(api.leaderboard).mockResolvedValue(manifest({
      rows: [{ label: "Ensemble", model: "moa/max", date: null, pass_k_rate: 1, mean_rate: 1,
        categories: {}, k: 3, scaffold: "baseline", seed: 0, harness: "ensemble" }],
    }));
    render(<Leaderboard />);
    expect(await screen.findByText("seed 0")).toBeInTheDocument();
    expect(screen.getByText("harness: ensemble")).toBeInTheDocument();
  });

  it("uses a manifest title when provided", async () => {
    vi.mocked(api.leaderboard).mockResolvedValue(manifest({ title: "September board" }));
    render(<Leaderboard />);
    expect(await screen.findByRole("heading", { name: "September board" })).toBeInTheDocument();
  });

  it("renders API errors", async () => {
    vi.mocked(api.leaderboard).mockRejectedValue(new Error("offline"));
    render(<Leaderboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("couldn't load the leaderboard: offline");
  });
});
