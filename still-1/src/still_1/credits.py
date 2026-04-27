"""Generate credit HTML files for each year group."""

import json
import logging
from pathlib import Path

from .classify import classify_images
from .config import DOWNLOADED_DIR, IMAGES_TS, METADATA_JSON, OUTPUT_DIR
from .match_files import build_id_to_path, match_entries_to_files
from .parse_images_ts import load_metadata_json, parse_images_ts, save_metadata_json
from .process import SKIP_IDS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_photographer(entry: dict) -> tuple[str, str]:
    """Get photographer name and profile URL from the sidecar JSON."""
    file_path = entry.get("file_path", "")
    if not file_path:
        return "", ""
    json_path = Path(file_path).with_suffix(".json")
    if not json_path.exists():
        return "", ""
    try:
        with open(json_path) as f:
            data = json.load(f)
        user = data.get("user", {})
        name = user.get("name", "")
        username = user.get("username", "")
        profile = f"https://unsplash.com/@{username}" if username else ""
        return name, profile
    except Exception:
        return "", ""


def write_all_credits_html(groups: dict[str, list[dict]], output_path: Path) -> None:
    """Write a single HTML file with all years."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for group_name, entries in groups.items():
        if not entries:
            continue
        lines.append(f"<h2>{group_name} ({len(entries)} images)</h2>")
        for entry in entries:
            desc = entry.get("description") or entry.get("id")
            link = entry.get("html_link", "")
            name, profile = get_photographer(entry)
            if name and profile:
                lines.append(
                    f'<a href="{link}">{desc}</a> by <a href="{profile}">{name}</a><br>'
                )
            else:
                lines.append(f'<a href="{link}">{desc}</a><br>')

    output_path.write_text("\n".join(lines))


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
    logger.info(f"Loaded {len(entries)} entries")

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

    credit_path = OUTPUT_DIR / "credits.html"
    write_all_credits_html(groups, credit_path)
    logger.info(f"  {credit_path}")
    logger.info("Done.")


if __name__ == "__main__":
    main()
