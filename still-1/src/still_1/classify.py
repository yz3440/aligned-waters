"""Classify images into groups by color temperature or year."""

import colorsys
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string to HSV (h: 0-360, s: 0-100, v: 0-100)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def classify_single(hex_color: str) -> str:
    """Classify a single hex color into warm/cool/neutral."""
    h, s, v = hex_to_hsv(hex_color)

    # Very dark -> neutral
    if v < 15:
        return "neutral"

    # Low saturation -> neutral
    if s <= 15:
        return "neutral"

    # Warm: reds, oranges, yellows, warm magentas
    if h <= 60 or h >= 300:
        return "warm"

    # Cool: blues, cyans, blue-greens
    if 170 <= h <= 270:
        return "cool"

    # Remaining (greens, teals, purples) -> neutral
    return "neutral"


def classify_images(
    entries: list[dict],
    mode: str = "color",
) -> dict[str, list[dict]]:
    """Split entries into groups.

    mode: "color" for warm/cool/neutral, "year" for grouping by year.
    """
    if mode == "year":
        return classify_by_year(entries)

    groups: dict[str, list[dict]] = {"warm": [], "cool": [], "neutral": []}

    for entry in entries:
        group = classify_single(entry.get("color", "#808080"))
        groups[group].append(entry)

    for name, items in groups.items():
        logger.info(f"  {name}: {len(items)} images")

    return groups


def classify_by_year(entries: list[dict]) -> dict[str, list[dict]]:
    """Split entries by the year in created_at."""
    groups: dict[str, list[dict]] = defaultdict(list)

    for entry in entries:
        created_at = entry.get("created_at", "")
        year = created_at[:4] if len(created_at) >= 4 else "unknown"
        groups[year].append(entry)

    # Sort by year
    sorted_groups = dict(sorted(groups.items()))

    for name, items in sorted_groups.items():
        logger.info(f"  {name}: {len(items)} images")

    return sorted_groups
