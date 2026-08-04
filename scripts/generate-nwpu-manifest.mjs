import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(".");
const DATASET_DIR = resolve(ROOT, "assets", "dataset_NWPU_VHR-10");
const OUTPUT_PATH = resolve(DATASET_DIR, "manifest.json");
const MAX_PER_CLASS = 4;
const TARGET_TOTAL = 40;

const CLASS_NAMES = {
  0: "airplane",
  1: "ship",
  2: "storage_tank",
  3: "baseball_diamond",
  4: "tennis_court",
  5: "basketball_court",
  6: "ground_track_field",
  7: "harbor",
  8: "bridge",
  9: "vehicle"
};

function parseLabelFile(fileName) {
  const fullPath = resolve(DATASET_DIR, fileName);
  const lines = readFileSync(fullPath, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const counts = new Map();
  for (const line of lines) {
    const [rawClassId] = line.split(/\s+/);
    const classId = Number(rawClassId);
    if (!Number.isInteger(classId) || CLASS_NAMES[classId] === undefined) {
      continue;
    }
    counts.set(classId, (counts.get(classId) ?? 0) + 1);
  }

  const classes = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0] - b[0])
    .map(([classId, count]) => ({
      classId,
      className: CLASS_NAMES[classId],
      count
    }));

  const primary = classes[0] ?? { classId: 9, className: "vehicle", count: 0 };
  const stem = fileName.replace(/\.txt$/i, "");

  return {
    id: stem,
    fileName: `${stem}.jpg`,
    relativePath: `dataset_NWPU_VHR-10/${stem}.jpg`,
    labelPath: `dataset_NWPU_VHR-10/${fileName}`,
    primaryClassId: primary.classId,
    primaryClassName: primary.className,
    classes,
    boxesCount: lines.length
  };
}

function buildManifest() {
  const labelFiles = readdirSync(DATASET_DIR)
    .filter((fileName) => fileName.toLowerCase().endsWith(".txt"))
    .sort((a, b) => a.localeCompare(b, "en"));

  const samples = labelFiles.map(parseLabelFile);
  const grouped = new Map();
  for (const sample of samples) {
    const bucket = grouped.get(sample.primaryClassName) ?? [];
    bucket.push(sample);
    grouped.set(sample.primaryClassName, bucket);
  }

  for (const bucket of grouped.values()) {
    bucket.sort((a, b) => b.boxesCount - a.boxesCount || a.fileName.localeCompare(b.fileName, "en"));
  }

  const curated = [];
  const seen = new Set();

  for (const className of Object.values(CLASS_NAMES)) {
    const bucket = grouped.get(className) ?? [];
    for (const sample of bucket.slice(0, MAX_PER_CLASS)) {
      curated.push(sample);
      seen.add(sample.id);
    }
  }

  if (curated.length < TARGET_TOTAL) {
    const remainder = samples
      .filter((sample) => !seen.has(sample.id))
      .sort((a, b) => b.boxesCount - a.boxesCount || a.fileName.localeCompare(b.fileName, "en"));

    for (const sample of remainder) {
      curated.push(sample);
      if (curated.length >= TARGET_TOTAL) {
        break;
      }
    }
  }

  curated.sort((a, b) => {
    if (a.primaryClassId !== b.primaryClassId) {
      return a.primaryClassId - b.primaryClassId;
    }
    return a.fileName.localeCompare(b.fileName, "en");
  });

  return curated;
}

const manifest = buildManifest();
writeFileSync(OUTPUT_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
console.log(`Generated ${manifest.length} curated samples at ${OUTPUT_PATH}`);
