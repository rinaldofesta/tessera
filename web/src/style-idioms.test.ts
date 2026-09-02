import { readdirSync, readFileSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(process.cwd(), "src");
const excluded = new Set([
  "api-types.gen.ts",
  "index.css",
  "lib/exportReport.ts",
  "lib/exportComparison.ts",
]);

function sourceFiles(dir = root): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (![".ts", ".tsx"].includes(extname(entry.name))) return [];
    const name = relative(root, path);
    return name.includes(".test.") || excluded.has(name) ? [] : [path];
  });
}

describe("source style idioms", () => {
  it("keeps application colours behind design tokens", () => {
    const failures = sourceFiles().flatMap((path) => {
      const source = readFileSync(path, "utf8");
      const matches = [
        ...source.matchAll(/#[0-9a-fA-F]{3,8}\b/g),
        ...source.matchAll(/\[var\(--/g),
        ...source.matchAll(/style=\{\{\s*(?:color|background)\s*:/g),
      ];
      return matches.map((match) => `${relative(root, path)}: ${match[0]}`);
    });
    expect(failures).toEqual([]);
  });

  it("keeps font loading self-hosted and the display face current", () => {
    const css = readFileSync(join(root, "index.css"), "utf8");
    expect(css).not.toContain(["Space", "Grotesk"].join(" "));
    expect(css).not.toContain(["google", "apis"].join(""));
  });
});
