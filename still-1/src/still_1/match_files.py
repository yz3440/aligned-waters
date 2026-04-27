"""Map Unsplash IDs to downloaded image file paths."""

import logging
from pathlib import Path

from .config import DOWNLOADED_DIR

logger = logging.getLogger(__name__)


def build_id_to_path(download_dir: Path = DOWNLOADED_DIR) -> dict[str, Path]:
    """Scan download directory, return {unsplash_id: Path} for .jpg files.

    Filenames follow: sea_horizon_{ID}_{photographer}.jpg
    IDs are 11 chars but may contain hyphens. We match by checking
    if the filename starts with 'sea_horizon_{id}_'.
    """
    all_jpgs = sorted(download_dir.glob("sea_horizon_*.jpg")) + sorted(
        download_dir.glob("sea_horizon_*.JPG")
    )

    # Build a dict keyed by extracted ID prefix
    # Since IDs can contain special chars, we index by prefix after 'sea_horizon_'
    path_lookup: dict[str, Path] = {}
    for p in all_jpgs:
        name = p.stem  # e.g. sea_horizon_ScAzpCG0vuE_H_M
        rest = name[len("sea_horizon_") :]  # ScAzpCG0vuE_H_M
        path_lookup[rest] = p

    return path_lookup


def match_entries_to_files(
    entries: list[dict], id_to_path: dict[str, Path]
) -> list[dict]:
    """Add 'file_path' to each entry that has a matching downloaded file.

    Returns only entries with matched files.
    """
    matched = []
    unmatched = 0

    for entry in entries:
        img_id = entry["id"]
        # Find the key that starts with this ID followed by '_'
        found = None
        for key, path in id_to_path.items():
            if key.startswith(img_id + "_") or key == img_id:
                found = path
                break

        if found:
            entry_copy = dict(entry)
            entry_copy["file_path"] = str(found)
            matched.append(entry_copy)
        else:
            unmatched += 1

    if unmatched:
        logger.warning(f"{unmatched} images had no matching downloaded file")

    logger.info(f"Matched {len(matched)} / {len(entries)} images to files")
    return matched
