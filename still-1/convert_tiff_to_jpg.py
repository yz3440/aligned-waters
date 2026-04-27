#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow"]
# ///

"""Convert all TIFF images in output/ to high-quality JPEG."""

from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

output_dir = Path(__file__).parent / "output"

for tiff_path in sorted(output_dir.glob("*.tiff")):
    jpg_path = tiff_path.with_suffix(".jpg")
    print(f"{tiff_path.name} -> {jpg_path.name}")
    img = Image.open(tiff_path)
    if img.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    else:
        img = img.convert("RGB")
    img.save(jpg_path, "JPEG", quality=95, subsampling=0)

print("Done.")
