import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent

# Pre-parsed image metadata (committed to the repo).
METADATA_JSON = PROJECT_ROOT / "data" / "images_metadata.json"

# Source TS file used to regenerate METADATA_JSON. Optional — only read if
# METADATA_JSON is missing.
IMAGES_TS = REPO_ROOT / "frontend" / "src" / "data" / "images.ts"

# Directory of high-res Unsplash JPGs (with sidecar JSON). Override with
# AW_DOWNLOAD_DIR; defaults to the sibling scraper output in this monorepo.
DOWNLOADED_DIR = Path(
    os.environ.get(
        "AW_DOWNLOAD_DIR",
        REPO_ROOT / "scraper" / "downloaded_images",
    )
)

OUTPUT_DIR = PROJECT_ROOT / "output"

# Output dimensions (3:2 aspect ratio)
LONG_EDGE = 6000
ASPECT_RATIO = (3, 2)
OUTPUT_W = 6000
OUTPUT_H = 4000

# Horizon alignment target: place horizon at 50% of output height
HORIZON_TARGET = 0.50

# Trimming
TRIM_PERCENTILE = 10
