# animation-1

Three.js generative animation for *Aligned Waters* — a horizontally-scrolling
collage of horizon-aligned photographs arranged in stacked strands.

## Setup

```bash
bun install
bun run setup   # populates public/images_resized/ (~80 MB, 3,152 images)
bun run dev     # http://localhost:5180
```

`bun run setup` looks for the image archive in this order:

1. `ASSETS_URL` env var — a downloadable `.zip` URL.
2. Sibling `../resizer/processed_images_256.zip` — present when this lives
   alongside the rest of the *Aligned Waters* monorepo.

The script extracts to `public/images_resized/`, stripping the `_256` suffix
so filenames match `public/manifest.json`.

## Scripts

- `bun run dev` — Vite dev server (port 5180)
- `bun run build` — production build to `dist/`
- `bun run preview` — preview the production build
- `bun run setup` — download + extract image assets

## Structure

- [src/main.ts](src/main.ts) — entry point, scene assembly, Tweakpane GUI
- [src/strand.ts](src/strand.ts) — one scrolling row of horizon-aligned strips
- [src/scene.ts](src/scene.ts) — renderer, orthographic camera, gradient background
- [src/config.ts](src/config.ts) — canvas size, duration, color constants
- [src/data.ts](src/data.ts) — manifest loader, round-robin pool splitter
- [public/manifest.json](public/manifest.json) — `{filename, width, height, horizon_y, created_at}` per image
