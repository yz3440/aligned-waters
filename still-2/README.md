# still-2

Archimedean spiral mosaic of *Aligned Waters* seascapes — each thumbnail rotated so its horizon follows the spiral curve.

## Setup

```bash
uv sync
```

Needs the high-resolution Unsplash JPGs. Default lookup path is the sibling `../scraper/downloaded_images/` (works inside the *Aligned Waters* monorepo). Override with `AW_DOWNLOAD_DIR`.

`data/images_metadata.json` is committed.

## Run

```bash
uv run spiral                       # full mosaic, 256px thumbs
uv run spiral --limit 200           # quick preview
uv run spiral --thumb-size 384 --overlap 0.2
```

Output goes to `output/spiral_{N}imgs_{px}px.jpg` (gitignored).
