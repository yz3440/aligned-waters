# still-1

Stacked average of *Aligned Waters* seascape photographs — one horizon-aligned composite per year.

## Setup

```bash
uv sync
```

This project needs the high-resolution Unsplash JPGs (with sidecar JSONs)
that match `data/images_metadata.json`. The default lookup path is the
sibling `../scraper/downloaded_images/` (works inside the *Aligned Waters*
monorepo). To point elsewhere:

```bash
export AW_DOWNLOAD_DIR=/path/to/downloaded_images
```

`data/images_metadata.json` (3,152 entries: id, dimensions, horizon_y,
created_at, html_link, description) is committed so you do not need
`frontend/src/data/images.ts` to run.

## Run

```bash
# Verify inputs without producing composites:
uv run averaging-photos --dry-run

# Generate per-year composites (writes to output/):
uv run averaging-photos --classify year

# Generate credits HTML for all years:
uv run averaging-credits

# Pack yearly composites into 4x3 and 1xN grids:
uv run averaging-grid
```

See `uv run averaging-photos --help` for all flags (method, aspect ratio,
horizon target, native-resolution mode, single-year filter, etc.).

## Outputs

`output/` (gitignored) contains:

- `composite_{year}_{N}imgs.{tiff,jpg}` — per-year averages
- `composite_{warm,cool,neutral}.{tiff,jpg}` — color-temperature averages (`--classify color`)
- `credits_{year}.html` and `credits.html` — image credits with Unsplash links
- `grid_{4x3,1xN}.{tiff,jpg}` — packed yearly grids

## Structure

- [src/still_1/main.py](src/still_1/main.py) — CLI entry, group + average pipeline
- [src/still_1/process.py](src/still_1/process.py) — averaging math, canvas sizing, horizon alignment
- [src/still_1/classify.py](src/still_1/classify.py) — color-temperature / year grouping
- [src/still_1/match_files.py](src/still_1/match_files.py) — Unsplash ID → file path lookup
- [src/still_1/parse_images_ts.py](src/still_1/parse_images_ts.py) — `images.ts` → JSON (only used to regenerate `data/images_metadata.json`)
- [src/still_1/grid.py](src/still_1/grid.py) — yearly grid packer
- [src/still_1/credits.py](src/still_1/credits.py) — HTML credits generator
- [src/still_1/config.py](src/still_1/config.py) — paths, output dimensions, defaults
- [data/images_metadata.json](data/images_metadata.json) — pre-parsed image metadata
