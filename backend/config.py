import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PHOTO_FOLDER = "/Users/thomasfitzgerald/landscape-design-search/optimized_images"
PHOTO_FOLDER = os.getenv("PHOTO_FOLDER", DEFAULT_PHOTO_FOLDER)

# Check if photo folder exists, if not, fallback to a 'photos' dir in project (for testing if user path invalid)
# Check if photo folder exists, if not, fallback to a 'photos' dir in project (for testing if user path invalid)
if not os.path.exists(PHOTO_FOLDER):
    print(f"WARNING: configured PHOTO_FOLDER {PHOTO_FOLDER} does not exist.")

# Persist data options
DEFAULT_DB_PATH = BASE_DIR / "landscape.db"
DEFAULT_THUMBNAILS_DIR = BASE_DIR / "backend/static/thumbnails"
DEFAULT_INDEX_PATH = BASE_DIR / "faiss_index.bin"

DB_PATH = Path(os.getenv("DB_PATH", DEFAULT_DB_PATH))
THUMBNAILS_DIR = Path(os.getenv("THUMBNAILS_DIR", DEFAULT_THUMBNAILS_DIR))
INDEX_PATH = Path(os.getenv("INDEX_PATH", DEFAULT_INDEX_PATH))

# Model
CLIP_MODEL_NAME = "clip-ViT-B-32" 

# Search
DEFAULT_TOP_K = 50

# Ensure directories exist
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
