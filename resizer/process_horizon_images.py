#!/usr/bin/env python3
"""
Process images with horizon labels:
1. Crop to the largest square centered on the horizon
2. Resize to 256x256 pixels
3. Process in parallel for efficiency
"""

import os
import sqlite3
from pathlib import Path
from PIL import Image
import numpy as np
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_horizon_images(db_path):
    """Get all images with horizon_y values from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT filename, width, height, horizon_y 
    FROM image 
    WHERE horizon_y IS NOT NULL
    ORDER BY filename
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return results


def crop_square_at_horizon(image, horizon_y_ratio):
    """
    Crop the largest square from the image centered at the horizon line.
    
    Args:
        image: PIL Image object
        horizon_y_ratio: Normalized horizon position (0.0 to 1.0)
    
    Returns:
        PIL Image object of the cropped square
    """
    width, height = image.size
    horizon_y_pixel = int(height * horizon_y_ratio)
    
    # Determine the maximum square size that can be centered at the horizon
    # The square is limited by the distance from horizon to the nearest edge
    max_size_from_top = 2 * horizon_y_pixel
    max_size_from_bottom = 2 * (height - horizon_y_pixel)
    max_size_from_sides = width
    
    # The actual square size is the minimum of these constraints
    square_size = min(max_size_from_top, max_size_from_bottom, max_size_from_sides)
    
    # Ensure we have a valid square size
    if square_size <= 0:
        logger.warning(f"Invalid square size {square_size}, using fallback center crop")
        square_size = min(width, height)
        horizon_y_pixel = height // 2
    
    # Calculate the crop box coordinates
    # Center the square horizontally
    left = (width - square_size) // 2
    right = left + square_size
    
    # Center the square vertically at the horizon
    top = horizon_y_pixel - square_size // 2
    bottom = top + square_size
    
    # Ensure coordinates are within image bounds
    if top < 0:
        bottom -= top
        top = 0
    if bottom > height:
        top -= (bottom - height)
        bottom = height
    if left < 0:
        right -= left
        left = 0
    if right > width:
        left -= (right - width)
        right = width
    
    # Crop the image
    cropped = image.crop((left, top, right, bottom))
    
    return cropped


def process_single_image(args):
    """
    Process a single image: crop and resize.
    
    Args:
        args: Tuple of (filename, width, height, horizon_y, input_dir, output_dir)
    
    Returns:
        Tuple of (success, filename, error_message)
    """
    filename, width, height, horizon_y, input_dir, output_dir = args
    
    try:
        # Construct full paths
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.replace('.jpg', '_256.jpg').replace('.JPG', '_256.jpg'))
        
        # Check if input file exists
        if not os.path.exists(input_path):
            return (False, filename, f"File not found: {input_path}")
        
        # Skip if output already exists (optional)
        # if os.path.exists(output_path):
        #     return (True, filename, "Already processed")
        
        # Open the image
        image = Image.open(input_path)
        
        # Verify dimensions match database
        if image.size != (width, height):
            logger.warning(f"Size mismatch for {filename}: DB says {width}x{height}, actual is {image.size}")
        
        # Crop square centered at horizon
        cropped = crop_square_at_horizon(image, horizon_y)
        
        # Resize to 256x256
        resized = cropped.resize((256, 256), Image.Resampling.LANCZOS)
        
        # Save the result
        resized.save(output_path, 'JPEG', quality=95)
        
        return (True, filename, None)
        
    except Exception as e:
        return (False, filename, str(e))


def process_images_parallel(db_path, input_dir, output_dir, num_workers=None):
    """
    Process all images with horizon labels in parallel.
    
    Args:
        db_path: Path to the SQLite database
        input_dir: Directory containing the original images
        output_dir: Directory to save the processed images
        num_workers: Number of parallel workers (None for auto)
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get list of images to process
    logger.info("Fetching image list from database...")
    images = get_horizon_images(db_path)
    logger.info(f"Found {len(images)} images with horizon labels")
    
    # Prepare arguments for parallel processing
    process_args = [
        (filename, width, height, horizon_y, input_dir, output_dir)
        for filename, width, height, horizon_y in images
    ]
    
    # Determine number of workers
    if num_workers is None:
        num_workers = min(cpu_count(), 8)  # Cap at 8 to avoid overwhelming the system
    
    logger.info(f"Starting parallel processing with {num_workers} workers...")
    
    # Process images in parallel with progress bar
    success_count = 0
    error_count = 0
    errors = []
    
    with Pool(num_workers) as pool:
        with tqdm(total=len(process_args), desc="Processing images") as pbar:
            for success, filename, error_msg in pool.imap_unordered(process_single_image, process_args):
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append((filename, error_msg))
                pbar.update(1)
                pbar.set_postfix({'Success': success_count, 'Errors': error_count})
    
    # Report results
    logger.info(f"\nProcessing complete!")
    logger.info(f"Successfully processed: {success_count} images")
    logger.info(f"Errors: {error_count} images")
    
    if errors:
        logger.error("\nErrors encountered:")
        for filename, error_msg in errors[:10]:  # Show first 10 errors
            logger.error(f"  {filename}: {error_msg}")
        if len(errors) > 10:
            logger.error(f"  ... and {len(errors) - 10} more errors")
    
    return success_count, error_count


def main():
    parser = argparse.ArgumentParser(description='Process horizon-labeled images')
    parser.add_argument('--db', default='horizon_labels.db', help='Path to SQLite database')
    parser.add_argument('--input-dir', default='downloaded_images', help='Input images directory')
    parser.add_argument('--output-dir', default='processed_images_256', help='Output directory for processed images')
    parser.add_argument('--workers', type=int, default=None, help='Number of parallel workers')
    parser.add_argument('--test', action='store_true', help='Test mode: process only first 10 images')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("Running in test mode (first 10 images only)")
        # Create a temporary test database with limited images
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM image WHERE horizon_y IS NOT NULL")
        total = cursor.fetchone()[0]
        conn.close()
        
        if total > 10:
            # Process only first 10 for testing
            import tempfile
            import shutil
            
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                tmp_db = tmp.name
            
            shutil.copy2(args.db, tmp_db)
            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()
            
            # Get first 10 images with horizon_y
            cursor.execute("""
                UPDATE image 
                SET horizon_y = NULL 
                WHERE filename NOT IN (
                    SELECT filename 
                    FROM image 
                    WHERE horizon_y IS NOT NULL 
                    ORDER BY filename 
                    LIMIT 10
                )
            """)
            conn.commit()
            conn.close()
            
            # Process with temporary database
            process_images_parallel(tmp_db, args.input_dir, args.output_dir, args.workers)
            
            # Clean up
            os.unlink(tmp_db)
        else:
            process_images_parallel(args.db, args.input_dir, args.output_dir, args.workers)
    else:
        process_images_parallel(args.db, args.input_dir, args.output_dir, args.workers)


if __name__ == '__main__':
    main()
