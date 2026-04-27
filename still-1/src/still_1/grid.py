"""Pack the 12 yearly composites into grids, horizon-aligned per row.

Each composite is downscaled so its longest edge is at most MAX_EDGE px.
Outputs both a 4x3 grid and a 1x12 single-row layout, as TIFF + JPEG.
"""

import logging
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

from .classify import classify_images
from .config import DOWNLOADED_DIR, IMAGES_TS, METADATA_JSON, OUTPUT_DIR
from .match_files import build_id_to_path, match_entries_to_files
from .parse_images_ts import load_metadata_json, parse_images_ts, save_metadata_json
from .process import SKIP_IDS, find_canvas_size

# Pillow refuses to load very large images by default
Image.MAX_IMAGE_PIXELS = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_EDGE = 6000  # max long edge per cell after downscaling


def find_tiff_for_year(year: str, output_dir: Path) -> Path | None:
    matches = sorted(output_dir.glob(f"composite_{year}_*imgs.tiff"))
    return matches[0] if matches else None


def load_and_scale_tiff(path: Path, max_edge: int) -> tuple[np.ndarray, float]:
    """Load TIFF, downscale if longest edge > max_edge. Returns (array, scale)."""
    arr = tifffile.imread(str(path))
    h, w = arr.shape[:2]
    long_edge = max(w, h)
    if long_edge <= max_edge:
        return arr, 1.0

    scale = max_edge / long_edge
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))

    # Pillow handles RGB and RGBA, including 16-bit per channel modes
    if arr.ndim == 3 and arr.shape[2] == 4:
        # Pillow needs separate handling per channel for 16-bit RGBA
        channels = [Image.fromarray(arr[:, :, i], mode="I;16") for i in range(4)]
        resized = [c.resize((new_w, new_h), Image.Resampling.LANCZOS) for c in channels]
        out = np.stack([np.asarray(c, dtype=np.uint16) for c in resized], axis=2)
    elif arr.ndim == 3 and arr.shape[2] == 3:
        channels = [Image.fromarray(arr[:, :, i], mode="I;16") for i in range(3)]
        resized = [c.resize((new_w, new_h), Image.Resampling.LANCZOS) for c in channels]
        out = np.stack([np.asarray(c, dtype=np.uint16) for c in resized], axis=2)
    else:
        img = Image.fromarray(arr, mode="I;16")
        out = np.asarray(img.resize((new_w, new_h), Image.Resampling.LANCZOS), dtype=np.uint16)

    return out, scale


JPEG_MAX_DIM = 65500


def save_jpeg(grid_uint16: np.ndarray, output_path: Path, quality: int = 92) -> None:
    """Flatten 16-bit RGB(A) array onto white, convert to 8-bit, save as JPEG.

    Auto-downscales if any dimension exceeds JPEG's 65500px limit.
    """
    if grid_uint16.ndim == 3 and grid_uint16.shape[2] == 4:
        alpha = grid_uint16[:, :, 3:4].astype(np.float32) / 65535.0
        rgb = grid_uint16[:, :, :3].astype(np.float32)
        white = 65535.0
        flat = rgb * alpha + white * (1.0 - alpha)
    else:
        flat = grid_uint16.astype(np.float32)

    flat_8 = np.clip(flat / 65535.0 * 255.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(flat_8, mode="RGB")

    # Downscale if needed to fit JPEG's dimension cap
    long_edge = max(img.size)
    if long_edge > JPEG_MAX_DIM:
        scale = JPEG_MAX_DIM / long_edge
        new_size = (int(img.width * scale), int(img.height * scale))
        logger.info(f"  Downscaling JPEG from {img.size} to {new_size} (>{JPEG_MAX_DIM}px)")
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    img.save(output_path, "JPEG", quality=quality, optimize=True)


def crop_to_content(arr: np.ndarray, horizon_row: int) -> tuple[np.ndarray, int]:
    """Crop array to bbox of non-transparent (or non-white) pixels.

    Returns (cropped_array, adjusted_horizon_row).
    For RGBA: bbox where alpha > 0.
    For RGB: bbox where any channel < 65535 (non-white).
    """
    if arr.ndim == 3 and arr.shape[2] == 4:
        mask = arr[:, :, 3] > 0
    else:
        # Non-white pixels
        mask = (arr[:, :, :3] < 65535).any(axis=2)

    if not mask.any():
        return arr, horizon_row

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    top = int(np.argmax(rows))
    bottom = len(rows) - int(np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = len(cols) - int(np.argmax(cols[::-1]))

    cropped = arr[top:bottom, left:right]
    new_horizon = horizon_row - top
    return cropped, new_horizon


def resize_uint16(arr: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
    """Resize uint16 RGB(A) array using Pillow per-channel."""
    n_ch = arr.shape[2] if arr.ndim == 3 else 1
    channels = [Image.fromarray(arr[:, :, i], mode="I;16") for i in range(n_ch)]
    resized = [c.resize((new_w, new_h), Image.Resampling.LANCZOS) for c in channels]
    return np.stack([np.asarray(c, dtype=np.uint16) for c in resized], axis=2)


def build_grid(cells: list, layout: list[list[int]]) -> np.ndarray:
    """Build a grid from cells given a layout (list of rows, each a list of cell indices).

    Each cell is upscaled to fill its column width (preserving aspect ratio),
    so there's no horizontal margin within columns.
    """
    rows = layout
    n_cols = max(len(r) for r in rows)

    # Per-column widths: max width across all rows for each column index
    col_widths = []
    for c in range(n_cols):
        widths = []
        for row in rows:
            if c < len(row):
                widths.append(cells[row[c]][2])
        col_widths.append(max(widths))
    col_offsets = [sum(col_widths[:c]) for c in range(n_cols)]
    grid_w = sum(col_widths)

    # Scale each cell up to its column width (preserving aspect)
    scaled_cells = {}  # (row_idx, col_idx) -> (year, img, w, h, horizon_row)
    for r, row in enumerate(rows):
        for c, idx in enumerate(row):
            year, img, w, h, horizon_row = cells[idx]
            target_w = col_widths[c]
            if w == target_w:
                scaled_cells[(r, c)] = (year, img, w, h, horizon_row)
            else:
                scale = target_w / w
                new_w = target_w
                new_h = int(round(h * scale))
                new_horizon = int(round(horizon_row * scale))
                logger.info(f"    Upscaling {year} from {w}x{h} to {new_w}x{new_h}")
                scaled_img = resize_uint16(img, new_w, new_h)
                scaled_cells[(r, c)] = (year, scaled_img, new_w, new_h, new_horizon)

    # Per-row heights and horizons (using scaled cells)
    row_heights = []
    row_horizons = []
    for r, row in enumerate(rows):
        row_cells = [scaled_cells[(r, c)] for c in range(len(row))]
        max_sky = max(cc[4] for cc in row_cells)
        max_water = max(cc[3] - cc[4] for cc in row_cells)
        row_heights.append(max_sky + max_water)
        row_horizons.append(max_sky)
    grid_h = sum(row_heights)

    logger.info(f"  Grid: {grid_w}x{grid_h}")
    logger.info(f"  Column widths: {col_widths}")
    logger.info(f"  Row heights: {row_heights}, horizons: {row_horizons}")

    sample = scaled_cells[(0, 0)][1]
    n_channels = sample.shape[2] if sample.ndim == 3 else 3

    if n_channels == 4:
        grid = np.zeros((grid_h, grid_w, 4), dtype=np.uint16)
    else:
        grid = np.full((grid_h, grid_w, 3), 65535, dtype=np.uint16)

    y_offset = 0
    for r, row in enumerate(rows):
        row_horizon = row_horizons[r]
        for c in range(len(row)):
            year, img, w, h, horizon_row = scaled_cells[(r, c)]
            dst_top = y_offset + (row_horizon - horizon_row)
            dst_left = col_offsets[c]  # cell now exactly fills column width
            grid[dst_top:dst_top + h, dst_left:dst_left + w] = img
            logger.info(f"    Placed {year} at ({dst_left},{dst_top})  {w}x{h}")
        y_offset += row_heights[r]

    return grid


def save_grid(grid: np.ndarray, basename: str) -> None:
    """Save grid as TIFF and JPEG."""
    tiff_path = OUTPUT_DIR / f"{basename}.tiff"
    jpeg_path = OUTPUT_DIR / f"{basename}.jpg"
    tifffile.imwrite(str(tiff_path), grid, photometric="rgb", compression="zlib")
    logger.info(f"  Saved {tiff_path.name}")
    save_jpeg(grid, jpeg_path)
    logger.info(f"  Saved {jpeg_path.name}")


def main():
    import sys

    if METADATA_JSON.exists():
        entries = load_metadata_json(METADATA_JSON)
    elif IMAGES_TS.exists():
        entries = parse_images_ts()
        save_metadata_json(entries, METADATA_JSON)
    else:
        logger.error(
            f"No metadata found. Expected committed file at {METADATA_JSON} "
            f"or source TS at {IMAGES_TS}."
        )
        sys.exit(1)

    if not DOWNLOADED_DIR.is_dir():
        logger.error(
            f"Downloaded images directory not found: {DOWNLOADED_DIR}\n"
            f"Set AW_DOWNLOAD_DIR to the directory containing sea_horizon_*.jpg files."
        )
        sys.exit(1)

    id_to_path = build_id_to_path()
    matched = match_entries_to_files(entries, id_to_path)
    matched = [e for e in matched if e.get("id") not in SKIP_IDS]
    groups = classify_images(matched, mode="year")

    years = sorted(groups.keys())
    logger.info(f"Years: {years}")

    # Load and downscale all yearly composites
    cells = []  # list of (year, img_array, w, h, horizon_row)
    for year in years:
        tiff_path = find_tiff_for_year(year, OUTPUT_DIR)
        if tiff_path is None:
            logger.warning(f"No TIFF for {year}, skipping")
            continue
        orig_w, orig_h, orig_horizon = find_canvas_size(groups[year], 0.5)
        img, scale = load_and_scale_tiff(tiff_path, MAX_EDGE)
        h, w = img.shape[:2]
        horizon_row = int(round(orig_horizon * scale))
        # Crop transparent / white margins so cell width = actual content width
        img, horizon_row = crop_to_content(img, horizon_row)
        h, w = img.shape[:2]
        logger.info(f"  {year}: {w}x{h} (cropped), horizon@{horizon_row}, scale={scale:.3f}")
        cells.append((year, img, w, h, horizon_row))

    n = len(cells)

    # 4x3 grid
    if n == 12:
        logger.info("\n=== Building 4x3 grid ===")
        layout_4x3 = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]
        grid_4x3 = build_grid(cells, layout_4x3)
        save_grid(grid_4x3, "grid_4x3")

    # 1xN single row
    logger.info(f"\n=== Building 1x{n} single-row grid ===")
    layout_1xn = [list(range(n))]
    grid_1xn = build_grid(cells, layout_1xn)
    save_grid(grid_1xn, f"grid_1x{n}")


if __name__ == "__main__":
    main()
