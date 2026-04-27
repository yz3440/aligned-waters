"""Core image processing: align, crop, accumulate, and output composites."""

import logging
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from tqdm import tqdm

logger = logging.getLogger(__name__)

SKIP_IDS = {"ef_V_EkW4zs"}  # 15000x15000 outlier that blows up canvas size


def align_and_crop(
    img: Image.Image,
    horizon_y: float,
    target_horizon: float,
    output_w: int,
    output_h: int,
) -> np.ndarray | None:
    """Align horizon to target position, crop to output aspect ratio, resize.

    Returns float64 numpy array of shape (output_h, output_w, 3), or None if
    the image cannot provide enough coverage.
    """
    w, h = img.size
    horizon_px = horizon_y * h

    scale = output_w / w

    sky_available = horizon_px * scale
    water_available = (h - horizon_px) * scale

    sky_needed = target_horizon * output_h
    water_needed = (1 - target_horizon) * output_h

    if sky_available < sky_needed * 0.5 or water_available < water_needed * 0.5:
        return None

    src_top = horizon_px - sky_needed / scale
    src_bottom = horizon_px + water_needed / scale

    if src_top < 0:
        src_top = 0
    if src_bottom > h:
        src_bottom = h

    src_left = 0
    src_right = w

    cropped = img.crop((int(src_left), int(src_top), int(src_right), int(src_bottom)))
    resized = cropped.resize((output_w, output_h), Image.Resampling.LANCZOS)

    return np.asarray(resized, dtype=np.float64)


def find_canvas_size(entries: list[dict], horizon_target: float) -> tuple[int, int]:
    """Find the canvas size needed to fit the largest image at native resolution.

    The canvas width = max image width.
    The canvas height is determined by the most sky and most water any single
    image contributes when horizons are aligned to horizon_target.
    """
    max_w = 0
    max_sky = 0  # pixels above horizon row
    max_water = 0  # pixels below horizon row

    for entry in entries:
        if entry.get("id") in SKIP_IDS:
            continue
        w, h = entry["width"], entry["height"]
        if w < h * 0.8:  # skip portraits
            continue
        horizon_px = entry["horizon_y"] * h
        sky = horizon_px
        water = h - horizon_px
        max_w = max(max_w, w)
        max_sky = max(max_sky, int(sky))
        max_water = max(max_water, int(water))

    # Make canvas square: side = max(width, height)
    canvas_h = max_sky + max_water
    side = max(max_w, canvas_h)

    # Pad height symmetrically around horizon if needed
    if side > canvas_h:
        extra = side - canvas_h
        extra_top = extra // 2
        max_sky += extra_top
        canvas_h = side

    # Pad width if needed (centering handles it, just expand canvas)
    canvas_w = side

    return canvas_w, canvas_h, max_sky


def place_native(
    img: Image.Image,
    horizon_y: float,
    canvas_w: int,
    canvas_h: int,
    horizon_row: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Place image at native resolution on the canvas, horizon-aligned and centered.

    Returns (pixels, mask) both of shape (canvas_h, canvas_w, 3).
    pixels has the image data, mask is 1.0 where the image covers, 0.0 elsewhere.
    """
    w, h = img.size
    pixels = np.asarray(img, dtype=np.float64)  # (h, w, 3)

    horizon_px = int(horizon_y * h)

    # Vertical placement: align image horizon to canvas horizon_row
    dst_top = horizon_row - horizon_px
    dst_bottom = dst_top + h

    # Horizontal placement: center
    dst_left = (canvas_w - w) // 2
    dst_right = dst_left + w

    # Clamp source and destination to canvas bounds
    src_y_start = 0
    src_y_end = h
    src_x_start = 0
    src_x_end = w

    if dst_top < 0:
        src_y_start = -dst_top
        dst_top = 0
    if dst_bottom > canvas_h:
        src_y_end -= dst_bottom - canvas_h
        dst_bottom = canvas_h
    if dst_left < 0:
        src_x_start = -dst_left
        dst_left = 0
    if dst_right > canvas_w:
        src_x_end -= dst_right - canvas_w
        dst_right = canvas_w

    if dst_top >= dst_bottom or dst_left >= dst_right:
        return None, None

    region = pixels[src_y_start:src_y_end, src_x_start:src_x_end, :]

    return region, (dst_top, dst_bottom, dst_left, dst_right)


def average_group_native(
    entries: list[dict],
    output_path: Path,
    horizon_target: float,
    method: str = "mean",
    trim_pct: int = 10,
    bg: str = "transparent",
) -> int:
    """Average a group keeping original pixel sizes (no resize).

    Canvas = largest width x (tallest sky + tallest water). Each image is
    placed at its native resolution, horizon-aligned and horizontally centered.
    Only the overlapping pixels contribute to each position's average.

    bg: "transparent" for RGBA output, "white" for RGB with white fill.
        Edge pixels naturally fade because fewer images cover them —
        alpha = count/max_count, no artificial cutoff.
    """
    canvas_w, canvas_h, horizon_row = find_canvas_size(entries, horizon_target)
    logger.info(f"Native canvas: {canvas_w}x{canvas_h}, horizon row: {horizon_row}")

    accumulator = np.zeros((canvas_h, canvas_w, 3), dtype=np.float64)
    count = np.zeros((canvas_h, canvas_w, 1), dtype=np.float64)

    if method == "trimmed_mean":
        mean_acc = np.zeros((canvas_h, canvas_w, 3), dtype=np.float64)
        m2_acc = np.zeros((canvas_h, canvas_w, 3), dtype=np.float64)
        n_acc = np.zeros((canvas_h, canvas_w, 1), dtype=np.float64)

    processed = 0
    skipped_load = 0
    skipped_place = 0
    skipped_portrait = 0

    desc = f"Pass 1 ({method})" if method == "trimmed_mean" else "Averaging (native)"

    for entry in tqdm(entries, desc=desc):
        file_path = entry.get("file_path")
        if not file_path:
            skipped_load += 1
            continue

        if entry.get("id") in SKIP_IDS:
            continue
        if entry["width"] < entry["height"] * 0.8:
            skipped_portrait += 1
            continue

        try:
            img = Image.open(file_path).convert("RGB")
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
            skipped_load += 1
            continue

        region, bounds = place_native(
            img, entry["horizon_y"], canvas_w, canvas_h, horizon_row
        )
        img.close()

        if region is None:
            skipped_place += 1
            continue

        t, b, l, r = bounds

        if method == "trimmed_mean":
            n_acc[t:b, l:r] += 1
            delta = region - mean_acc[t:b, l:r]
            mean_acc[t:b, l:r] += delta / n_acc[t:b, l:r]
            delta2 = region - mean_acc[t:b, l:r]
            m2_acc[t:b, l:r] += delta * delta2
        else:
            accumulator[t:b, l:r] += region
            count[t:b, l:r] += 1

        processed += 1

    if method == "trimmed_mean" and processed > 2:
        variance = m2_acc / np.maximum(n_acc - 1, 1)
        stddev = np.sqrt(variance)
        z = {5: 1.645, 10: 1.282, 15: 1.036, 20: 0.842}.get(trim_pct, 1.282)
        lower = mean_acc - z * stddev
        upper = mean_acc + z * stddev

        accumulator = np.zeros((canvas_h, canvas_w, 3), dtype=np.float64)
        count = np.zeros((canvas_h, canvas_w, 1), dtype=np.float64)

        for entry in tqdm(entries, desc="Pass 2 (trimmed, native)"):
            file_path = entry.get("file_path")
            if not file_path:
                continue
            if entry["width"] < entry["height"] * 0.8:
                continue
            try:
                img = Image.open(file_path).convert("RGB")
            except Exception:
                continue

            region, bounds = place_native(
                img, entry["horizon_y"], canvas_w, canvas_h, horizon_row
            )
            img.close()
            if region is None:
                continue

            t, b, l, r = bounds
            local_lower = lower[t:b, l:r]
            local_upper = upper[t:b, l:r]
            mask = (region >= local_lower) & (region <= local_upper)
            mask_all = mask.all(axis=2, keepdims=True).astype(np.float64)
            accumulator[t:b, l:r] += region * mask_all
            count[t:b, l:r] += mask_all

    # Compute average and natural alpha from coverage count
    safe_count = np.maximum(count, 1)
    result = accumulator / safe_count  # (H, W, 3), float64, 0-255 range

    # Binary alpha: fully opaque wherever any image covers, transparent elsewhere
    max_count = count.max()
    alpha_f = (count[:, :, 0] > 0).astype(np.float64)  # (H, W), 0 or 1

    covered_pixels = int(alpha_f.sum())
    total_pixels = canvas_w * canvas_h
    logger.info(
        f"Coverage: {covered_pixels}/{total_pixels} pixels "
        f"({100*covered_pixels/total_pixels:.1f}%), "
        f"max overlap: {int(max_count)} images"
    )

    result_f = result * (65535.0 / 255.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if bg == "transparent":
        alpha_16 = np.clip(alpha_f * 65535.0, 0, 65535).astype(np.uint16)
        rgb_16 = np.clip(result_f, 0, 65535).astype(np.uint16)
        # Zero out RGB where no coverage
        has_coverage = count[:, :, 0] > 0
        for c in range(3):
            rgb_16[:, :, c] = np.where(has_coverage, rgb_16[:, :, c], 0)
        rgba = np.concatenate([rgb_16, alpha_16[:, :, np.newaxis]], axis=2)
        tifffile.imwrite(str(output_path), rgba, photometric="rgb")
    elif bg == "white":
        white = 65535.0
        alpha_3 = alpha_f[:, :, np.newaxis]
        blended = result_f * alpha_3 + white * (1.0 - alpha_3)
        result_16 = np.clip(blended, 0, 65535).astype(np.uint16)
        tifffile.imwrite(str(output_path), result_16, photometric="rgb")
    else:
        # black background
        alpha_3 = alpha_f[:, :, np.newaxis]
        blended = result_f * alpha_3
        result_16 = np.clip(blended, 0, 65535).astype(np.uint16)
        tifffile.imwrite(str(output_path), result_16, photometric="rgb")

    logger.info(
        f"Saved {output_path.name}: {canvas_w}x{canvas_h}, bg={bg}, "
        f"{processed} images averaged, "
        f"{skipped_portrait} portrait skipped, "
        f"{skipped_place} placement skipped, "
        f"{skipped_load} load failures"
    )

    return processed


def average_group(
    entries: list[dict],
    output_path: Path,
    output_w: int,
    output_h: int,
    horizon_target: float,
    method: str = "mean",
    trim_pct: int = 10,
) -> int:
    """Process one temperature group. Returns count of images averaged."""
    accumulator = np.zeros((output_h, output_w, 3), dtype=np.float64)
    count = np.zeros((output_h, output_w, 1), dtype=np.float64)

    # For trimmed mean: first pass collects mean and M2 (Welford's)
    if method == "trimmed_mean":
        mean_acc = np.zeros((output_h, output_w, 3), dtype=np.float64)
        m2_acc = np.zeros((output_h, output_w, 3), dtype=np.float64)
        n_acc = np.zeros((output_h, output_w, 1), dtype=np.float64)

    processed = 0
    skipped_load = 0
    skipped_crop = 0
    skipped_portrait = 0

    desc = f"Pass 1 ({method})" if method == "trimmed_mean" else "Averaging"

    for entry in tqdm(entries, desc=desc):
        file_path = entry.get("file_path")
        if not file_path:
            skipped_load += 1
            continue

        # Skip extreme portrait images
        if entry.get("id") in SKIP_IDS:
            continue
        if entry["width"] < entry["height"] * 0.8:
            skipped_portrait += 1
            continue

        try:
            img = Image.open(file_path).convert("RGB")
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
            skipped_load += 1
            continue

        pixels = align_and_crop(img, entry["horizon_y"], horizon_target, output_w, output_h)
        img.close()

        if pixels is None:
            skipped_crop += 1
            continue

        if method == "trimmed_mean":
            # Welford's online algorithm
            n_acc += 1
            delta = pixels - mean_acc
            mean_acc += delta / n_acc
            delta2 = pixels - mean_acc
            m2_acc += delta * delta2
        else:
            accumulator += pixels
            count += 1

        processed += 1

    if method == "trimmed_mean" and processed > 2:
        # Second pass: trimmed mean
        variance = m2_acc / np.maximum(n_acc - 1, 1)
        stddev = np.sqrt(variance)

        # Percentile bounds using normal approximation
        # For 10th/90th percentile: z ≈ 1.28
        z = {5: 1.645, 10: 1.282, 15: 1.036, 20: 0.842}.get(trim_pct, 1.282)
        lower = mean_acc - z * stddev
        upper = mean_acc + z * stddev

        # Reset accumulators for second pass
        accumulator = np.zeros((output_h, output_w, 3), dtype=np.float64)
        count = np.zeros((output_h, output_w, 1), dtype=np.float64)

        for entry in tqdm(entries, desc="Pass 2 (trimmed)"):
            file_path = entry.get("file_path")
            if not file_path:
                continue
            if entry["width"] < entry["height"] * 0.8:
                continue

            try:
                img = Image.open(file_path).convert("RGB")
            except Exception:
                continue

            pixels = align_and_crop(
                img, entry["horizon_y"], horizon_target, output_w, output_h
            )
            img.close()

            if pixels is None:
                continue

            # Mask: include pixel only if within bounds (per channel)
            mask = (pixels >= lower) & (pixels <= upper)
            # All 3 channels must be in range
            mask_all = mask.all(axis=2, keepdims=True).astype(np.float64)

            accumulator += pixels * mask_all
            count += mask_all

    if method != "trimmed_mean":
        # Already accumulated
        pass

    # Compute average
    count = np.maximum(count, 1)  # avoid division by zero
    result = accumulator / count

    # Scale to 16-bit (0-255 -> 0-65535)
    result_16 = np.clip(result * (65535.0 / 255.0), 0, 65535).astype(np.uint16)

    # Save as 16-bit TIFF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(output_path), result_16, photometric="rgb")

    logger.info(
        f"Saved {output_path.name}: {processed} images averaged, "
        f"{skipped_portrait} portrait skipped, "
        f"{skipped_crop} crop skipped, "
        f"{skipped_load} load failures"
    )

    return processed
