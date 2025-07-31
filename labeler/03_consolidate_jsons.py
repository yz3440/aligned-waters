#!/usr/bin/env python3
"""
Script to export labeled sea horizon images and users to JSON files.
Exports only labeled images with non-null horizon_y and deduplicates users.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect("horizon_labels.db")


def get_labeled_images_with_horizon() -> List[Dict]:
    """Get all labeled images with non-null horizon_y."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, filename, image_id, width, height, metadata_json, horizon_y
        FROM image 
        WHERE is_labeled = TRUE AND horizon_y IS NOT NULL
        ORDER BY id
    """
    )

    rows = cursor.fetchall()
    conn.close()

    images = []
    for row in rows:
        metadata = json.loads(row[5])
        images.append(
            {
                "db_id": row[0],
                "filename": row[1],
                "image_id": row[2],
                "width": row[3],
                "height": row[4],
                "metadata": metadata,
                "horizon_y": row[6],
            }
        )

    return images


def format_image_for_export(image_data: Dict) -> Dict:
    """Format image data for export according to the specified schema."""
    metadata = image_data["metadata"]

    # Extract user information
    user = metadata.get("user", {})
    user_id = user.get("id")

    # Get regular image URL
    urls = metadata.get("urls", {})
    regular_image_src = urls.get("regular", "")

    # Get HTML link
    links = metadata.get("links", {})
    html_link = links.get("html", "")

    return {
         "id": image_data["image_id"],
         "slug": metadata.get("slug", ""),
         "created_at": metadata.get("created_at", ""),
         "color": metadata.get("color", ""),
         "description": metadata.get("description"),
         "alt_description": metadata.get("alt_description", ""),
         "regular_image_src": regular_image_src,
         "html_link": html_link,
         "user_id": user_id,
         "width": image_data["width"],
         "height": image_data["height"],
         "horizon_y": image_data["horizon_y"],
     }


def extract_users_from_images(images: List[Dict]) -> List[Dict]:
    """Extract and deduplicate users from images."""
    users_seen: Set[str] = set()
    users = []

    for image_data in images:
        metadata = image_data["metadata"]
        user = metadata.get("user", {})
        user_id = user.get("id")

        # Skip if no user_id or already seen
        if not user_id or user_id in users_seen:
            continue

        users_seen.add(user_id)

        # Get profile image
        profile_image = user.get("profile_image", {})
        profile_image_src = profile_image.get("medium", "")

        # Get HTML link
        links = user.get("links", {})
        html_link = links.get("html", "")

        users.append(
            {
                "id": user_id,
                "username": user.get("username", ""),
                "name": user.get("name", ""),
                "location": user.get("location"),
                "html_link": html_link,
                "profile_image_src": profile_image_src,
            }
        )

    return users


def export_to_json():
    """Export database to JSON files."""
    print("Exporting labeled images and users to JSON files...")

    # Get labeled images with horizon
    images_data = get_labeled_images_with_horizon()
    print(f"Found {len(images_data)} labeled images with horizon")

    if not images_data:
        print("No labeled images with horizon found!")
        return

    # Format images for export
    images_export = []
    for image_data in images_data:
        try:
            formatted_image = format_image_for_export(image_data)
            images_export.append(formatted_image)
        except Exception as e:
            print(f"Error formatting image {image_data['image_id']}: {e}")
            continue

    # Extract and deduplicate users
    users_export = extract_users_from_images(images_data)
    print(f"Found {len(users_export)} unique users")

    # Write images.json
    with open("images.json", "w", encoding="utf-8") as f:
        json.dump(images_export, f, indent=2, ensure_ascii=False)

    # Write users.json
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users_export, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported {len(images_export)} images to images.json")
    print(f"✅ Exported {len(users_export)} users to users.json")

    # Show some statistics
    print("\n📊 Export Statistics:")
    print(f"  - Total labeled images with horizon: {len(images_export)}")
    print(f"  - Unique users: {len(users_export)}")

    # Show sample of exported data
    if images_export:
        print(f"\n📸 Sample image export:")
        sample_image = images_export[0]
        print(f"  - ID: {sample_image['id']}")
        print(f"  - Slug: {sample_image['slug']}")
        print(f"  - Horizon Y: {sample_image['horizon_y']}")
        print(f"  - User ID: {sample_image['user_id']}")

    if users_export:
        print(f"\n👤 Sample user export:")
        sample_user = users_export[0]
        print(f"  - ID: {sample_user['id']}")
        print(f"  - Username: {sample_user['username']}")
        print(f"  - Name: {sample_user['name']}")
        print(f"  - Location: {sample_user['location']}")


def main():
    """Main function."""
    print("=== Sea Horizon Database Export Tool ===")

    # Check if database exists
    if not Path("horizon_labels.db").exists():
        print("❌ Error: horizon_labels.db not found!")
        print("Please run 01-generate-db.py first to create the database.")
        return

    # Export data
    export_to_json()

    print("\n🎉 Export complete!")
    print("Files created:")
    print("  - images.json: Labeled images with horizon positions")
    print("  - users.json: Unique users from labeled images")


if __name__ == "__main__":
    main()
