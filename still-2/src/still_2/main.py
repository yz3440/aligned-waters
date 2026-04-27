"""Arrange horizon-aligned seascape thumbnails along an Archimedean spiral."""

import argparse
import json
import logging
import math
import os
import sys
from pathlib import Path

from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent

META_JSON = PROJECT_ROOT / "data" / "images_metadata.json"
DOWNLOADED = Path(
    os.environ.get(
        "AW_DOWNLOAD_DIR",
        REPO_ROOT / "scraper" / "downloaded_images",
    )
)
OUTPUT_DIR = PROJECT_ROOT / "output"

SKIP_IDS = {"ef_V_EkW4zs"}  # 15000x15000 outlier

Image.MAX_IMAGE_PIXELS = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def pad_horizon_centered(img: Image.Image, horizon_y_ratio: float) -> Image.Image:
    """Pad image with transparency so horizon ends up at vertical center.

    Returns RGBA image. Original pixels stay opaque; padded regions are transparent.
    """
    img = img.convert("RGBA")
    w, h = img.size
    hy = int(horizon_y_ratio * h)
    top_pad = max(0, h - 2 * hy)
    bottom_pad = max(0, 2 * hy - h)
    new_h = h + top_pad + bottom_pad
    out = Image.new("RGBA", (w, new_h), (0, 0, 0, 0))
    out.paste(img, (0, top_pad))
    return out


def find_file(img_id: str) -> Path | None:
    matches = list(DOWNLOADED.glob(f"sea_horizon_{img_id}_*.jpg"))
    if matches:
        return matches[0]
    matches = list(DOWNLOADED.glob(f"sea_horizon_{img_id}_*.JPG"))
    return matches[0] if matches else None


def archimedean_spiral(n: int, cell_size: int) -> list[tuple[float, float, float]]:
    """Generate n (x, y, tangent_angle_deg) entries along an Archimedean spiral.

    r(θ) = b·θ where b = cell_size/(2π); cells are placed at constant arc-length
    intervals so neighbors along the spiral are tangent. The tangent angle is the
    direction of motion along the spiral at each placement, used to rotate
    each image so its horizon follows the spiral curve.
    """
    b = cell_size / (2 * math.pi)
    out: list[tuple[float, float, float]] = []

    theta = 2 * math.pi  # start one full turn out so r >= cell_size
    arc_since_last = 0.0
    dtheta = 0.001

    while len(out) < n:
        r = b * theta
        ds = math.sqrt(r * r + b * b) * dtheta
        arc_since_last += ds
        if arc_since_last >= cell_size:
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            # Tangent vector
            dxdt = b * math.cos(theta) - r * math.sin(theta)
            dydt = b * math.sin(theta) + r * math.cos(theta)
            # Negate because canvas y-axis is down (PIL rotates CCW in screen coords)
            angle = -math.degrees(math.atan2(dydt, dxdt))
            out.append((x, y, angle))
            arc_since_last = 0.0
        theta += dtheta

    return out


def main():
    parser = argparse.ArgumentParser(description="Spiral mosaic of horizon images")
    parser.add_argument("--thumb-size", type=int, default=256, help="Thumbnail edge in px")
    parser.add_argument("--quality", type=int, default=88, help="JPEG quality 1-100")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of images")
    parser.add_argument("--overlap", type=float, default=0.15,
                        help="Fraction of overlap between neighbors (0=touching, 0.15=15%%)")
    args = parser.parse_args()

    if not META_JSON.exists():
        logger.error(f"Metadata not found: {META_JSON}")
        sys.exit(1)
    if not DOWNLOADED.is_dir():
        logger.error(
            f"Downloaded images directory not found: {DOWNLOADED}\n"
            f"Set AW_DOWNLOAD_DIR to the directory containing sea_horizon_*.jpg files."
        )
        sys.exit(1)

    meta = json.loads(META_JSON.read_text())
    meta = [e for e in meta if e["id"] not in SKIP_IDS]
    if args.limit:
        meta = meta[: args.limit]
    logger.info(f"{len(meta)} candidate images")

    # Reduce effective spacing to make neighbors overlap
    spacing = max(1, int(args.thumb_size * (1 - args.overlap)))
    positions = archimedean_spiral(len(meta), spacing)

    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    # Uncropped images padded vertically can be up to ~3x thumb_size on long edge,
    # so use generous margin to fit rotated overlap at canvas edges.
    margin = int(args.thumb_size * 3)
    min_x = min(xs) - margin
    max_x = max(xs) + margin
    min_y = min(ys) - margin
    max_y = max(ys) + margin
    canvas_w = int(max_x - min_x)
    canvas_h = int(max_y - min_y)
    logger.info(f"Canvas: {canvas_w}x{canvas_h}")

    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")

    placed = 0
    skipped = 0
    for entry, (px, py, angle) in tqdm(list(zip(meta, positions)), desc="Placing"):
        img_path = find_file(entry["id"])
        if not img_path:
            skipped += 1
            continue
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception:
            skipped += 1
            continue
        # Pad so horizon is at vertical center, then scale so width = thumb_size
        padded = pad_horizon_centered(img, entry["horizon_y"])
        img.close()
        pw, ph = padded.size
        scale = args.thumb_size / pw
        new_w = args.thumb_size
        new_h = max(1, int(round(ph * scale)))
        scaled = padded.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Rotate around center (= horizon row, since we padded to center it)
        rotated = scaled.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        rw, rh = rotated.size
        cx = int(px - min_x - rw / 2)
        cy = int(py - min_y - rh / 2)
        canvas.paste(rotated, (cx, cy), rotated)
        placed += 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"spiral_{placed}imgs_{args.thumb_size}px.jpg"
    canvas.save(out_path, "JPEG", quality=args.quality, optimize=True)
    logger.info(f"Saved {out_path}")
    logger.info(f"  {canvas_w}x{canvas_h}, {placed} placed, {skipped} skipped")


if __name__ == "__main__":
    main()
