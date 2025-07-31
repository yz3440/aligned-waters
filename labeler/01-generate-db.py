#!/usr/bin/env python3
"""
Script to generate SQLite database for sea horizon image labeling.
Creates a table with image metadata and labeling status.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

def create_database(db_path: str = "horizon_labels.db"):
    """Create the SQLite database with the image table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the image table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            image_id TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            metadata_json TEXT NOT NULL,
            horizon_y REAL,
            is_labeled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_id ON image(image_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_labeled ON image(is_labeled)")
    
    conn.commit()
    conn.close()
    print(f"Database created: {db_path}")

def process_images(images_dir: str, db_path: str = "horizon_labels.db"):
    """Process all images and their metadata JSON files."""
    images_path = Path(images_dir)
    
    if not images_path.exists():
        print(f"Error: Images directory {images_dir} does not exist")
        return
    
    # Get all JSON files
    json_files = list(images_path.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to process")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    processed_count = 0
    skipped_count = 0
    
    for json_file in json_files:
        try:
            # Read JSON metadata
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract required fields
            image_id = metadata.get('id')
            width = metadata.get('width')
            height = metadata.get('height')
            
            if not all([image_id, width, height]):
                print(f"Warning: Missing required fields in {json_file.name}")
                skipped_count += 1
                continue
            
            # Check if corresponding image file exists
            image_filename = json_file.stem + '.jpg'
            image_path = json_file.parent / image_filename
            
            if not image_path.exists():
                print(f"Warning: Image file {image_filename} not found for {json_file.name}")
                skipped_count += 1
                continue
            
            # Check if already exists in database
            cursor.execute("SELECT id FROM image WHERE filename = ?", (image_filename,))
            if cursor.fetchone():
                print(f"Skipping {image_filename} - already in database")
                skipped_count += 1
                continue
            
            # Insert into database
            cursor.execute("""
                INSERT INTO image (filename, image_id, width, height, metadata_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                image_filename,
                image_id,
                width,
                height,
                json.dumps(metadata, ensure_ascii=False)
            ))
            
            processed_count += 1
            print(f"Processed: {image_filename}")
            
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            skipped_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nProcessing complete:")
    print(f"  - Processed: {processed_count}")
    print(f"  - Skipped: {skipped_count}")
    print(f"  - Total: {processed_count + skipped_count}")

def show_database_stats(db_path: str = "horizon_labels.db"):
    """Show statistics about the database."""
    conn = sqlite3.connect(db_path)
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
    cursor.execute("SELECT COUNT(*) FROM image WHERE is_labeled = TRUE AND horizon_y IS NULL")
    bad_images = cursor.fetchone()[0]
    
    # Images to be labeled
    cursor.execute("SELECT COUNT(*) FROM image WHERE is_labeled = FALSE")
    images_to_label = cursor.fetchone()[0]
    
    print(f"\nDatabase Statistics:")
    print(f"  - Total images: {total_images}")
    print(f"  - Labeled images: {labeled_images}")
    print(f"  - Images with horizon: {images_with_horizon}")
    print(f"  - Bad images (no horizon): {bad_images}")
    print(f"  - Images to be labeled: {images_to_label}")
    
    conn.close()

def main():
    """Main function to run the database generation."""
    # Configuration
    images_dir = "../scraper/downloaded_images"
    db_path = "horizon_labels.db"
    
    print("=== Sea Horizon Image Labeling Database Generator ===")
    
    # Create database
    print("\n1. Creating database...")
    create_database(db_path)
    
    # Process images
    print("\n2. Processing images...")
    process_images(images_dir, db_path)
    
    # Show statistics
    print("\n3. Database statistics:")
    show_database_stats(db_path)
    
    print(f"\nDatabase ready: {db_path}")
    print("\nNext steps:")
    print("  - Use the labeling tool to mark horizon positions")
    print("  - horizon_y should be normalized between 0-1 (0 = top, 1 = bottom)")
    print("  - Set is_labeled = TRUE when done")
    print("  - If no horizon exists, set is_labeled = TRUE and horizon_y = NULL")

if __name__ == "__main__":
    main() 