import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(".");
const GEO_JSON = resolve(ROOT, "assets", "sample_100_mix", "geo.json");
const OUTPUT = resolve(ROOT, "assets", "sample_100_mix", "manifest.json");

const geo = JSON.parse(readFileSync(GEO_JSON, "utf8"));
const images = geo.images;
const manifest = [];

for (const [key, record] of Object.entries(images)) {
  const r = record;
  manifest.push({
    fileName: `${key}.jpg`,
    relativePath: `sample_100_mix/${key}.jpg`,
    split: r.split.toLowerCase(),
    centerLon: r.center[0],
    centerLat: r.center[1],
    resolutionXm: r.resolution.x_m,
    resolutionYm: r.resolution.y_m,
  });
}

manifest.sort((a, b) => a.fileName.localeCompare(b.fileName));
writeFileSync(OUTPUT, JSON.stringify(manifest, null, 2));
console.log(`Generated ${manifest.length} entries to ${OUTPUT}`);
