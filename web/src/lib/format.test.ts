import { describe, expect, it } from "vitest";
import { pct, shortModel } from "./format";

describe("pct", () => {
  it("renders a 0…1 rate as a whole percent", () => {
    expect(pct(0.72)).toBe("72%");
  });
  it("renders a dash for missing rates", () => {
    expect(pct(null)).toBe("—");
    expect(pct(undefined)).toBe("—");
  });
});

describe("shortModel", () => {
  it("drops the provider prefix", () => {
    expect(shortModel("anthropic/claude-sonnet-4")).toBe("claude-sonnet-4");
  });
  it("passes bare names through", () => {
    expect(shortModel("qwen3-32b")).toBe("qwen3-32b");
  });
});
