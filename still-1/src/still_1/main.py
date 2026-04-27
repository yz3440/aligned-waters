"""CLI entry point for averaging photos."""

import argparse
import logging
import sys
from pathlib import Path

from .classify import classify_images
from .config import (
    DOWNLOADED_DIR,
    HORIZON_TARGET,
    IMAGES_TS,
    LONG_EDGE,
    METADATA_JSON,
    OUTPUT_DIR,
    TRIM_PERCENTILE,
)
from .match_files import build_id_to_path, match_entries_to_files
from .parse_images_ts import load_metadata_json, parse_images_ts, save_metadata_json
from .process import average_group, average_group_native

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def write_credits_html(entries: list[dict], group_name: str, output_path: Path) -> None:
    """Write an HTML file listing all images with links to Unsplash."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!DOCTYPE html>",
        "<html><head>",
        f"<title>Credits — {group_name} ({len(entries)} images)</title>",
        "<style>body{font-family:system-ui;max-width:800px;margin:2em auto;line-height:1.6}"
        "a{color:#0066cc}li{margin:0.3em 0}</style>",
        "</head><body>",
        f"<h1>{group_name} — {len(entries)} images</h1>",
        "<ol>",
    ]
    for entry in entries:
        desc = entry.get("description") or entry.get("id")
        link = entry.get("html_link", "")
        lines.append(f'  <li><a href="{link}">{desc}</a></li>')
    lines += ["</ol>", "</body></html>"]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Produce averaged composite images from Aligned Waters dataset"
    )
    parser.add_argument(
        "--method",
        choices=["mean", "trimmed_mean"],
        default="mean",
        help="Averaging method (default: mean)",
    )
    parser.add_argument(
        "--trim-pct",
        type=int,
        default=TRIM_PERCENTILE,
        help="Percentile to trim for trimmed_mean (default: 10)",
    )
    parser.add_argument(
        "--long-edge",
        type=int,
        default=LONG_EDGE,
        help="Long edge in pixels (default: 6000)",
    )
    parser.add_argument(
        "--aspect",
        default="3:2",
        help="Aspect ratio W:H (default: 3:2)",
    )
    parser.add_argument(
        "--horizon-target",
        type=float,
        default=HORIZON_TARGET,
        help="Where to place horizon (0-1, default: 0.5)",
    )
    parser.add_argument(
        "--classify",
        choices=["color", "year"],
        default="year",
        help="Grouping method: color (warm/cool/neutral) or year (default: color)",
    )
    parser.add_argument(
        "--native-res",
        action="store_true",
        help="Keep original pixel sizes; canvas = largest image in pool",
    )
    parser.add_argument(
        "--bg",
        choices=["transparent", "white", "black"],
        default="transparent",
        help="Background for sparse pixels in native-res mode (default: transparent)",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Only process a single year (e.g. --year 2020)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, match, classify, and report counts without processing",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for TIFFs",
    )

    args = parser.parse_args()

    # Parse aspect ratio
    try:
        aw, ah = map(int, args.aspect.split(":"))
    except ValueError:
        logger.error(f"Invalid aspect ratio: {args.aspect}")
        sys.exit(1)

    # Compute output dimensions
    if aw >= ah:
        output_w = args.long_edge
        output_h = int(args.long_edge * ah / aw)
    else:
        output_h = args.long_edge
        output_w = int(args.long_edge * aw / ah)

    logger.info(f"Output: {output_w}x{output_h} ({args.aspect})")

    # Step 1: Load metadata
    if METADATA_JSON.exists():
        logger.info(f"Loading metadata from {METADATA_JSON}")
        entries = load_metadata_json(METADATA_JSON)
    elif IMAGES_TS.exists():
        logger.info(f"Parsing {IMAGES_TS}...")
        entries = parse_images_ts()
        save_metadata_json(entries, METADATA_JSON)
    else:
        logger.error(
            f"No metadata found. Expected committed file at {METADATA_JSON} "
            f"or source TS at {IMAGES_TS}."
        )
        sys.exit(1)
    logger.info(f"Loaded {len(entries)} image entries")

    # Step 2: Match to downloaded files
    if not DOWNLOADED_DIR.is_dir():
        logger.error(
            f"Downloaded images directory not found: {DOWNLOADED_DIR}\n"
            f"Set AW_DOWNLOAD_DIR to the directory containing sea_horizon_*.jpg files."
        )
        sys.exit(1)
    logger.info(f"Scanning {DOWNLOADED_DIR}...")
    id_to_path = build_id_to_path()
    logger.info(f"Found {len(id_to_path)} downloaded images")

    matched = match_entries_to_files(entries, id_to_path)

    # Step 3: Classify
    logger.info("Classifying by color temperature...")
    groups = classify_images(matched, mode=args.classify)

    # Report
    total = sum(len(g) for g in groups.values())
    logger.info(f"Total matched and classified: {total}")
    for name, items in groups.items():
        logger.info(f"  {name}: {len(items)} images")

    # Filter to single year if specified
    if args.year:
        if args.year in groups:
            groups = {args.year: groups[args.year]}
        else:
            logger.error(f"Year {args.year} not found. Available: {', '.join(groups.keys())}")
            return

    # Generate credit HTML for each group
    for group_name, group_entries in groups.items():
        if not group_entries:
            continue
        credit_path = args.output_dir / f"credits_{group_name}.html"
        write_credits_html(group_entries, group_name, credit_path)
        logger.info(f"Credits: {credit_path}")

    if args.dry_run:
        return

    # Step 4: Process each group
    summary = {}
    for group_name, group_entries in groups.items():
        if not group_entries:
            logger.warning(f"Skipping empty group: {group_name}")
            continue

        output_path = args.output_dir / f"composite_{group_name}_{len(group_entries)}imgs.tiff"
        logger.info(f"\nProcessing {group_name} ({len(group_entries)} images)...")

        if args.native_res:
            count = average_group_native(
                group_entries,
                output_path=output_path,
                horizon_target=args.horizon_target,
                method=args.method,
                trim_pct=args.trim_pct,
                bg=args.bg,
            )
        else:
            count = average_group(
                group_entries,
                output_path=output_path,
                output_w=output_w,
                output_h=output_h,
                horizon_target=args.horizon_target,
                method=args.method,
                trim_pct=args.trim_pct,
            )
        summary[group_name] = count

    # Print summary
    logger.info("\n=== Summary ===")
    for name, count in summary.items():
        logger.info(f"  {name}: {count} images averaged -> composite_{name}.tiff")
    logger.info(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
