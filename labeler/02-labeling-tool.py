#!/usr/bin/env python3
"""
FastAPI web tool for labeling sea horizon images.
Interactive interface with mouse clicking and keyboard shortcuts.
"""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pydantic import BaseModel

# Configuration
IMAGES_DIR = "../scraper/downloaded_images"
DB_PATH = "horizon_labels.db"

app = FastAPI(title="Sea Horizon Labeling Tool")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="static/images"), name="images")

# Templates
templates = Jinja2Templates(directory="templates")


class LabelUpdate(BaseModel):
    image_id: int
    horizon_y: Optional[float] = None
    is_labeled: bool = True


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def get_unlabeled_images(limit: int = 1) -> List[Dict]:
    """Get unlabeled images from database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, filename, image_id, width, height, metadata_json
        FROM image 
        WHERE is_labeled = FALSE 
        ORDER BY id 
        LIMIT ?
    """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    images = []
    for row in rows:
        images.append(
            {
                "id": row[0],
                "filename": row[1],
                "image_id": row[2],
                "width": row[3],
                "height": row[4],
                "metadata": json.loads(row[5]),
            }
        )

    return images


def get_last_labeled_image() -> Optional[Dict]:
    """Get the most recently labeled image for undo functionality."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, filename, image_id, width, height, metadata_json, horizon_y, is_labeled
        FROM image 
        WHERE is_labeled = TRUE 
        ORDER BY updated_at DESC 
        LIMIT 1
    """
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "filename": row[1],
            "image_id": row[2],
            "width": row[3],
            "height": row[4],
            "metadata": json.loads(row[5]),
            "horizon_y": row[6],
            "is_labeled": row[7],
        }

    return None


def update_image_label(
    image_id: int, horizon_y: Optional[float], is_labeled: bool = True
):
    """Update image label in database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE image 
        SET horizon_y = ?, is_labeled = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """,
        (horizon_y, is_labeled, image_id),
    )

    conn.commit()
    conn.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main labeling interface."""
    return templates.TemplateResponse("labeling.html", {"request": request})


@app.get("/api/next-image")
async def get_next_image():
    """Get next unlabeled image."""
    images = get_unlabeled_images(limit=1)

    if not images:
        return {"message": "No more images to label!", "image": None}

    image = images[0]
    return {
        "image": {
            "id": image["id"],
            "filename": image["filename"],
            "image_id": image["image_id"],
            "width": image["width"],
            "height": image["height"],
            "url": f"/images/{image['filename']}",
            "metadata": image["metadata"],
        }
    }


@app.post("/api/label")
async def label_image(label_data: LabelUpdate):
    """Update image label."""
    try:
        update_image_label(
            image_id=label_data.image_id,
            horizon_y=label_data.horizon_y,
            is_labeled=label_data.is_labeled,
        )
        return {"success": True, "message": "Label updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/undo")
async def undo_last_label():
    """Get the last labeled image for undo functionality."""
    image = get_last_labeled_image()

    if not image:
        return {"message": "No labeled images to undo!", "image": None}

    return {
        "image": {
            "id": image["id"],
            "filename": image["filename"],
            "image_id": image["image_id"],
            "width": image["width"],
            "height": image["height"],
            "url": f"/images/{image['filename']}",
            "metadata": image["metadata"],
            "horizon_y": image["horizon_y"],
            "is_labeled": image["is_labeled"],
        }
    }


@app.get("/api/stats")
async def get_stats():
    """Get labeling statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total images
    cursor.execute("SELECT COUNT(*) FROM image")
    total_images = cursor.fetchone()[0]

    # Labeled images
    cursor.execute("SELECT COUNT(*) FROM image WHERE is_labeled = TRUE")
    labeled_images = cursor.fetchone()[0]

    # Images with horizon
    cursor.execute("SELECT COUNT(*) FROM image WHERE horizon_y IS NOT NULL")
    images_with_horizon = cursor.fetchone()[0]

    # Images without horizon (labeled as bad)
    cursor.execute(
        "SELECT COUNT(*) FROM image WHERE is_labeled = TRUE AND horizon_y IS NULL"
    )
    bad_images = cursor.fetchone()[0]

    # Images to be labeled
    cursor.execute("SELECT COUNT(*) FROM image WHERE is_labeled = FALSE")
    images_to_label = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total_images,
        "labeled": labeled_images,
        "with_horizon": images_with_horizon,
        "bad_images": bad_images,
        "to_label": images_to_label,
        "progress": (
            round((labeled_images / total_images) * 100, 1) if total_images > 0 else 0
        ),
    }


if __name__ == "__main__":
    # Create static directories if they don't exist
    os.makedirs("static/images", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

    # Create symlink to images directory
    images_symlink = Path("static/images")
    if not images_symlink.exists():
        try:
            os.symlink(Path(IMAGES_DIR), images_symlink)
        except OSError:
            # If symlink fails, copy a few images for testing
            print(
                "Creating symlink failed. Please manually copy images to static/images/"
            )

    print("Starting labeling tool...")
    print("Open http://localhost:8000 in your browser")
    print("Keyboard shortcuts:")
    print("  - Click on image to mark horizon position")
    print("  - Press 'h' to confirm horizon label and go to next")
    print("  - Press 's' to skip (mark as no horizon) and go to next")
    print("  - Press 'u' to undo last label")
    print("  - Press 'r' to reload current image")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
