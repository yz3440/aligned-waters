#!/usr/bin/env python3
"""
Unsplash Image Downloader
Downloads images from Unsplash based on keyword search.
"""

import os
import requests
import json
import argparse
from urllib.parse import urlparse
from pathlib import Path
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
)

# Load environment variables from .env file
load_dotenv()


def should_retry_exception(exception):
    """Check if an exception should trigger a retry."""
    import ssl
    from requests.exceptions import RequestException, SSLError, ConnectionError, Timeout

    # Retry on various network and SSL errors
    if isinstance(exception, (RequestException, SSLError, ConnectionError, Timeout)):
        return True

    # Retry on SSL-specific errors
    if isinstance(exception, ssl.SSLError):
        return True

    # Retry on connection pool errors
    if "Max retries exceeded" in str(exception):
        return True

    return False


class UnsplashDownloader:
    def __init__(self, access_key: str, download_dir: str = "downloaded_images"):
        """
        Initialize the Unsplash downloader.

        Args:
            access_key: Your Unsplash API access key
            download_dir: Directory to save downloaded images
        """
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        # Headers for API requests
        self.headers = {
            "Authorization": f"Client-ID {access_key}",
            "Accept-Version": "v1",
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(should_retry_exception),
        reraise=True,
    )
    def _make_request(
        self, url: str, params: Dict = None, stream: bool = False
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            url: URL to request
            params: Query parameters
            stream: Whether to stream the response

        Returns:
            Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        response = requests.get(url, headers=self.headers, params=params, stream=stream)
        response.raise_for_status()
        return response

    def search_photos(
        self, query: str, per_page: int = 30, page: int = 1
    ) -> Optional[Dict]:
        """
        Search for photos on Unsplash.

        Args:
            query: Search query
            per_page: Number of photos per page (max 30)
            page: Page number

        Returns:
            API response or None if failed
        """
        url = f"{self.base_url}/search/photos"
        params = {"query": query, "per_page": min(per_page, 30), "page": page}

        try:
            response = self._make_request(url, params=params)
            return response.json()
        except requests.RequestException as e:
            print(f"Error searching photos after retries: {e}")
            return None

    def save_metadata(self, photo_data: Dict, filename_base: str) -> bool:
        """
        Save photo metadata as JSON file.

        Args:
            photo_data: Photo data from Unsplash API
            filename_base: Base filename without extension

        Returns:
            True if successful, False otherwise
        """
        json_filename = f"{filename_base}.json"
        json_filepath = self.download_dir / json_filename

        # Check if JSON file already exists
        if json_filepath.exists():
            print(f"Skipped metadata (already exists): {json_filename}")
            return True

        try:
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(photo_data, f, indent=2, ensure_ascii=False)

            print(f"Saved metadata: {json_filename}")
            return True

        except Exception as e:
            print(f"Error saving metadata {json_filename}: {e}")
            return False

    def download_image(self, image_url: str, filename: str) -> bool:
        """
        Download an image from URL.

        Args:
            image_url: URL of the image to download
            filename: Filename to save the image as

        Returns:
            True if successful, False otherwise
        """
        filepath = self.download_dir / filename

        # Check if file already exists
        if filepath.exists():
            print(f"Skipped (already exists): {filename}")
            return True

        try:
            response = self._make_request(image_url, stream=True)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Downloaded: {filename}")
            return True

        except requests.RequestException as e:
            print(f"Error downloading {filename} after retries: {e}")
            return False

    def download_photos_by_keyword(
        self,
        keyword: str,
        max_photos: int = 50,
        quality: str = "raw",
        page_offset: int = 0,
    ) -> int:
        """
        Download photos by keyword search.

        Args:
            keyword: Search keyword
            max_photos: Maximum number of photos to download
            quality: Image quality ('raw', 'full', 'regular', 'small', 'thumb')
            page_offset: Page offset to start from (0 = start from page 1, 1 = start from page 2, etc.)

        Returns:
            Number of successfully downloaded photos
        """
        print(f"Searching for photos with keyword: '{keyword}'")
        print(f"Maximum photos to download: {max_photos}")
        print(f"Image quality: {quality}")
        print(f"Starting from page: {page_offset + 1}")

        downloaded_count = 0
        page = page_offset + 1  # Start from the specified page

        while downloaded_count < max_photos:
            print(f"\nFetching page {page}...")

            # Search for photos
            search_result = self.search_photos(keyword, per_page=30, page=page)

            if not search_result:
                print(f"Failed to fetch page {page}, skipping to next page...")
                page += 1
                continue

            if not search_result.get("results"):
                print("No more photos found.")
                break

            photos = search_result["results"]

            if not photos:
                print("No photos found on this page.")
                break

            # Download photos from this page
            for photo in photos:
                if downloaded_count >= max_photos:
                    break

                # Get photo details
                photo_id = photo["id"]

                # Get image URL based on quality preference
                if quality in photo["urls"]:
                    photo_url = photo["urls"][quality]
                else:
                    print(
                        f"Warning: Quality '{quality}' not available, using 'raw' instead"
                    )
                    photo_url = photo["urls"]["raw"]

                photographer = photo["user"]["name"]

                # Create filename
                file_extension = self._get_file_extension(photo_url)
                filename = f"{keyword.replace(' ', '_')}_{photo_id}_{photographer.replace(' ', '_')}{file_extension}"
                filename_base = filename.rsplit(".", 1)[
                    0
                ]  # Remove extension for metadata file

                # Save metadata
                self.save_metadata(photo, filename_base)

                # Download the image
                if self.download_image(photo_url, filename):
                    downloaded_count += 1

                # Rate limiting - Unsplash allows 50 requests per hour for demo apps
                time.sleep(0.1)  # Small delay to be respectful

            page += 1

        print(f"\nDownload completed! Downloaded {downloaded_count} photos.")
        print(f"Photos saved in: {self.download_dir.absolute()}")
        return downloaded_count

    def _get_file_extension(self, url: str) -> str:
        """Extract file extension from URL."""
        parsed = urlparse(url)
        path = parsed.path
        if "." in path:
            return "." + path.split(".")[-1]
        return ".jpg"  # Default to .jpg if no extension found


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download images from Unsplash based on keyword search"
    )
    parser.add_argument(
        "--keyword",
        "-k",
        type=str,
        default="computer desk setup monitor",
        help="Search keyword (default: 'desk setup')",
    )
    parser.add_argument(
        "--max-photos",
        "-m",
        type=int,
        default=500,
        help="Maximum number of photos to download (default: 500)",
    )
    parser.add_argument(
        "--quality",
        "-q",
        type=str,
        default="raw",
        choices=["raw", "full", "regular", "small", "thumb"],
        help="Image quality: raw (original), full, regular, small, thumb (default: raw)",
    )
    parser.add_argument(
        "--download-dir",
        "-d",
        type=str,
        default="downloaded_images",
        help="Directory to save downloaded images (default: downloaded_images)",
    )
    parser.add_argument(
        "--page-offset",
        "-p",
        type=int,
        default=0,
        help="Page offset to start from (0 = start from page 1, 1 = start from page 2, etc.). Useful when hitting rate limits (50 req/hour).",
    )

    return parser.parse_args()


def main():
    """Main function to run the downloader."""
    print("Unsplash Image Downloader")
    print("=" * 40)

    # Parse command line arguments
    args = parse_arguments()

    # Get API key from environment variables
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")

    if not access_key:
        print("Error: UNSPLASH_ACCESS_KEY not found in environment variables!")
        print("\nPlease make sure you have a .env file with:")
        print("UNSPLASH_ACCESS_KEY=your_access_key_here")
        print("UNSPLASH_SECRET_KEY=your_secret_key_here")
        print("UNSPLASH_APP_ID=your_app_id_here")
        print("\nTo get these keys:")
        print("1. Go to https://unsplash.com/developers")
        print("2. Create an account and register your application")
        print("3. Get your keys from the dashboard")
        return

    # Initialize downloader
    downloader = UnsplashDownloader(access_key, args.download_dir)

    try:
        downloaded_count = downloader.download_photos_by_keyword(
            args.keyword, args.max_photos, args.quality, args.page_offset
        )
        print(f"\nSuccessfully downloaded {downloaded_count} images!")

    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    main()
