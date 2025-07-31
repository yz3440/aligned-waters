# Sea Horizon Labeling Tool

A web-based tool for labeling sea horizon positions in images using FastAPI and interactive mouse clicking.

## Features

- **Interactive Image Labeling**: Click on images to mark horizon positions
- **Keyboard Shortcuts**: Quick navigation and labeling
- **Real-time Statistics**: Track labeling progress
- **Database Integration**: SQLite database for storing labels
- **Modern UI**: Clean, responsive web interface

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Database** (if not already done):
   ```bash
   python 01-generate-db.py
   ```

3. **Start the Labeling Tool**:
   ```bash
   python 02-labeling-tool.py
   ```

4. **Open in Browser**:
   Navigate to `http://localhost:8000`

## How to Use

### Labeling Process

1. **Load Image**: The tool automatically loads the next unlabeled image
2. **Mark Horizon**: Click on the image where the sea horizon line is located
3. **Confirm**: Press `H` or click "Confirm Horizon" to save the label and move to next image
4. **Skip**: Press `G` or click "Skip Image" if the image has no clear horizon

### Keyboard Shortcuts

- **`H`**: Confirm horizon position and go to next image
- **`G`**: Skip current image (mark as no horizon) and go to next image  
- **`R`**: Reload current image (clear current selection)

### Visual Feedback

- **Red Line**: Shows the marked horizon position
- **Red Circle**: Marks the exact click point
- **Progress Bar**: Shows overall labeling progress
- **Statistics**: Real-time counts of labeled images

## Database Schema

The tool uses a SQLite database (`horizon_labels.db`) with the following structure:

```sql
CREATE TABLE image (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    image_id TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    horizon_y REAL,           -- Normalized Y position (0-1)
    is_labeled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Label Values

- **`horizon_y`**: Normalized Y position (0 = top of image, 1 = bottom)
- **`is_labeled`**: Whether the image has been processed
- **`horizon_y = NULL`**: Image marked as having no horizon
- **`horizon_y = 0.5`**: Horizon at middle of image

## File Structure

```
labeler/
├── 01-generate-db.py          # Database generation script
├── 02-labeling-tool.py        # FastAPI web application
├── requirements.txt           # Python dependencies
├── horizon_labels.db          # SQLite database (generated)
├── templates/
│   └── labeling.html          # Web interface template
├── static/
│   └── images/                # Symlink to downloaded images
└── README.md                  # This file
```

## API Endpoints

- **`GET /`**: Main labeling interface
- **`GET /api/next-image`**: Get next unlabeled image
- **`POST /api/label`**: Save image label
- **`GET /api/stats`**: Get labeling statistics

## Troubleshooting

### Images Not Loading
- Ensure the symlink to `../scraper/downloaded_images` exists
- Check that images are in the correct directory
- Verify database contains image records

### Database Issues
- Run `01-generate-db.py` to recreate the database
- Check file permissions for the database file

### Web Interface Issues
- Clear browser cache
- Check browser console for JavaScript errors
- Ensure port 8000 is not in use

## Statistics

The tool tracks:
- **Total Images**: All images in the database
- **Labeled Images**: Images that have been processed
- **With Horizon**: Images that have a horizon position marked
- **Bad Images**: Images marked as having no horizon
- **To Label**: Remaining images to process
- **Progress**: Percentage of images labeled

## Tips for Efficient Labeling

1. **Use Keyboard Shortcuts**: Much faster than clicking buttons
2. **Look for Clear Horizons**: Focus on images with distinct sea-sky boundaries
3. **Skip Unclear Images**: Don't force labels on ambiguous images
4. **Take Breaks**: Labeling can be repetitive, take regular breaks
5. **Check Progress**: Monitor statistics to track your progress 