import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import { runFixture } from "./test/fixtures";

afterEach(() => vi.unstubAllGlobals());

describe("run API", () => {
  it("returns the server Run without an adapter", async () => {
    const run = runFixture();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(run))));
    await expect(api.getRun("run-1")).resolves.toEqual(run);
  });

  it("posts dry-run specs and comparisons with the default intervention", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}")));
    vi.stubGlobal("fetch", fetchMock);
    const spec = runFixture().request;
    await api.dryRun(spec);
    await api.compareRuns("a", "b");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/runs/dry-run", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(spec),
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/comparisons", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ a: "a", b: "b", intervention: "model" }),
    });
  });
});
