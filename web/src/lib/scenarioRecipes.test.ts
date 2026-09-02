import { describe, expect, it } from "vitest";
import { CONFLICT, SUITE_COPY } from "@/copy";
import type { Blueprint } from "@/types";
import {
  RECIPE_SPECS,
  buildRecipe,
  claimId,
  humanize,
  isoDaysAgo,
  isoNow,
  probeId,
  slug,
  uniqueId,
} from "./scenarioRecipes";

const EMPTY_BLUEPRINT: Blueprint = { claims: [], probes: [] };

describe("scenario recipe identifiers", () => {
  it("normalizes slugs and human-readable labels deterministically", () => {
    expect(slug("  Acme Support / EMEA  ")).toBe("acme_support_emea");
    expect(slug("---")).toBe("x");
    expect(humanize("renewalDate_value-v2")).toBe("renewal date value v2");
    expect(humanize(" renewalDate_value-v2 ")).toBe(humanize("renewalDate_value-v2"));
  });

  it("builds deterministic claim and probe ids", () => {
    expect(claimId("Acme Corp", "renewal date", "crm")).toBe("acme_corp__renewal_date__crm");
    expect(probeId("Acme Corp", "renewal date")).toBe("q__acme_corp__renewal_date");
    expect(claimId("Acme Corp", "renewal date", "crm")).toBe(claimId("Acme Corp", "renewal date", "crm"));
  });

  it("reserves unique ids with stable numeric suffixes", () => {
    const ids = new Set(["fact", "fact_2"]);
    expect(uniqueId("fact", ids)).toBe("fact_3");
    expect(uniqueId("fact", ids)).toBe("fact_4");
    expect(ids).toEqual(new Set(["fact", "fact_2", "fact_3", "fact_4"]));
  });
});

describe("scenario recipe dates", () => {
  it("emits fixed UTC ISO timestamp shapes", () => {
    expect(isoDaysAgo(30)).toMatch(/^\d{4}-\d{2}-\d{2}T09:00:00Z$/);
    expect(isoNow()).toMatch(/^\d{4}-\d{2}-\d{2}T14:30:00Z$/);
  });
});

describe("buildRecipe", () => {
  for (const key of Object.keys(RECIPE_SPECS) as Array<keyof typeof RECIPE_SPECS>) {
    it(`builds a coherent ${key} scenario from example fields`, () => {
      const spec = RECIPE_SPECS[key];
      const fields = {
        ...Object.fromEntries(spec.fields.map((field) => [field.key, field.placeholder ?? `${field.key} example`])),
        assertedAt: "2026-09-02T14:30:00Z",
        assertedAtA: "2026-06-04T09:00:00Z",
        assertedAtB: "2026-09-02T14:30:00Z",
      };

      const first = buildRecipe(key, fields, EMPTY_BLUEPRINT);
      const second = buildRecipe(key, fields, EMPTY_BLUEPRINT);
      const ids = [...first.claims.map((claim) => claim.claim_id), ...first.probes.map((probe) => probe.probe_id)];
      const claimIds = new Set(first.claims.map((claim) => claim.claim_id));

      expect(first).toEqual(second);
      expect(new Set(ids).size).toBe(ids.length);
      expect(first.probes).toHaveLength(1);
      expect(first.probes[0].conflict_type).toBe(SUITE_COPY.RECIPE_CONFLICT[key]);
      expect(first.probes[0].expected_behavior).toBe(CONFLICT[SUITE_COPY.RECIPE_CONFLICT[key]].behavior);
      expect((first.probes[0].expected_sources ?? []).every((id) => claimIds.has(id))).toBe(true);
    });
  }
});
