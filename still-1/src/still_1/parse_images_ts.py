"""Parse frontend/src/data/images.ts into Python dicts."""

import json
import re
from pathlib import Path

from .config import IMAGES_TS


def parse_images_ts(ts_path: Path = IMAGES_TS) -> list[dict]:
    """Extract image entries from the TypeScript file using regex per field."""
    text = ts_path.read_text()

    # Split into individual object blocks
    blocks = re.split(r"\},\s*\{", text)

    entries = []
    for block in blocks:
        entry = {}

        m = re.search(r'id:\s*"([^"]+)"', block)
        if not m:
            continue
        entry["id"] = m.group(1)

        m = re.search(r'color:\s*"([^"]+)"', block)
        entry["color"] = m.group(1) if m else "#808080"

        m = re.search(r"width:\s*(\d+)", block)
        entry["width"] = int(m.group(1)) if m else 0

        m = re.search(r"height:\s*(\d+)", block)
        entry["height"] = int(m.group(1)) if m else 0

        m = re.search(r'created_at:\s*"([^"]+)"', block)
        entry["created_at"] = m.group(1) if m else ""

        m = re.search(r'description:\s*"([^"]*)"', block)
        entry["description"] = m.group(1) if m else ""

        # html_link value is on the next line in the TS
        m = re.search(r'html_link:\s*\n?\s*"([^"]+)"', block)
        entry["html_link"] = m.group(1) if m else ""

        m = re.search(r"horizon_y:\s*([0-9.]+)", block)
        if not m:
            continue
        entry["horizon_y"] = float(m.group(1))

        entries.append(entry)

    return entries


def save_metadata_json(entries: list[dict], output_path: Path) -> None:
    """Save parsed entries to JSON for caching."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, indent=2))


def load_metadata_json(json_path: Path) -> list[dict]:
    """Load cached metadata JSON."""
    return json.loads(json_path.read_text())
