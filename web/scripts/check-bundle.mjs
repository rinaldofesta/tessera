import { readdir, stat } from "node:fs/promises";
import { join } from "node:path";

const limit = 1_000_000;
const assets = join(process.cwd(), "..", "src", "tessera", "data", "web", "assets");

let files;
try {
  files = (await readdir(assets)).filter((name) => name.endsWith(".js"));
} catch {
  console.error(
    "Bundle check failed: src/tessera/data/web/assets is missing. Run npm run build first.",
  );
  process.exit(1);
}

const total = (await Promise.all(files.map(async (name) => (await stat(join(assets, name))).size)))
  .reduce((sum, size) => sum + size, 0);

console.log(`JavaScript bundle total: ${total} bytes (limit: ${limit} bytes)`);
if (total > limit) {
  console.error(`Bundle budget exceeded by ${total - limit} bytes.`);
  process.exit(1);
}
