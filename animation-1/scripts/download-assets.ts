#!/usr/bin/env bun
// Populate public/images_resized/ from the resized-image zip.
//
// Source resolution:
//   1. ASSETS_URL env var (https URL) — downloaded into a temp file.
//   2. Sibling ../resizer/processed_images_256.zip — used in-place.
//
// The zip stores files as `processed_images_256/<name>_256.jpg`. We strip
// the `processed_images_256/` prefix and the `_256` filename suffix so
// keys match `manifest.json` filenames.

import { mkdir, rm, stat } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(SCRIPT_DIR, "..");
const TARGET = join(ROOT, "public", "images_resized");
const SIBLING_ZIP = resolve(ROOT, "..", "resizer", "processed_images_256.zip");

async function fileExists(p: string): Promise<boolean> {
  try {
    await stat(p);
    return true;
  } catch {
    return false;
  }
}

async function resolveZip(): Promise<{ path: string; cleanup?: () => Promise<void> }> {
  const url = process.env.ASSETS_URL;
  if (url) {
    console.log(`Downloading assets from ${url}`);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Download failed: ${res.status} ${res.statusText}`);
    const tmpPath = join(tmpdir(), `animation-1-assets-${Date.now()}.zip`);
    await Bun.write(tmpPath, res);
    return { path: tmpPath, cleanup: () => rm(tmpPath, { force: true }) };
  }

  if (await fileExists(SIBLING_ZIP)) {
    console.log(`Using sibling zip: ${SIBLING_ZIP}`);
    return { path: SIBLING_ZIP };
  }

  throw new Error(
    `No asset source found. Either:\n` +
      `  - set ASSETS_URL to a downloadable zip URL, or\n` +
      `  - place the zip at ${SIBLING_ZIP}`,
  );
}

async function extract(zipPath: string) {
  await mkdir(TARGET, { recursive: true });
  // Use system `unzip` — works on macOS/Linux out of the box, fast on
  // multi-thousand-file archives, and avoids pulling in a JS unzip dep.
  const proc = Bun.spawn(["unzip", "-o", "-q", zipPath, "-d", TARGET], {
    stdout: "inherit",
    stderr: "inherit",
  });
  const code = await proc.exited;
  if (code !== 0) throw new Error(`unzip exited with code ${code}`);

  // Flatten: zip contains processed_images_256/<file>_256.jpg.
  // Move into TARGET and strip _256 suffix to match manifest.json.
  const inner = join(TARGET, "processed_images_256");
  if (!(await fileExists(inner))) {
    throw new Error(`Expected ${inner} after unzip — archive structure changed?`);
  }

  const glob = new Bun.Glob("*.jpg");
  let count = 0;
  for await (const name of glob.scan({ cwd: inner })) {
    const stripped = name.replace(/_256\.jpg$/, ".jpg");
    const src = join(inner, name);
    const dst = join(TARGET, stripped);
    await Bun.write(dst, Bun.file(src));
    count++;
  }
  await rm(inner, { recursive: true, force: true });
  console.log(`Extracted ${count} images to public/images_resized/`);
}

const { path, cleanup } = await resolveZip();
try {
  await extract(path);
} finally {
  if (cleanup) await cleanup();
}
