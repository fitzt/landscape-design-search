import os
import sys
import hashlib
import time
import shutil
from pathlib import Path
from datetime import datetime
import argparse

import numpy as np
from PIL import Image
import exifread
import faiss
from sentence_transformers import SentenceTransformer

# Add parent directory to path to allow importing backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import PHOTO_FOLDER, THUMBNAILS_DIR, INDEX_PATH, CLIP_MODEL_NAME
from backend.db import init_db, upsert_image, get_all_images_map, delete_image, get_db_connection

# Supported image extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

def calculate_file_hash(filepath, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()

def get_exif_date(filepath):
    try:
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
            date_str = str(tags.get('EXIF DateTimeOriginal', ''))
            if date_str:
                # Format: YYYY:MM:DD HH:MM:SS
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').isoformat()
    except Exception as e:
        print(f"Error reading EXIF for {filepath}: {e}")
    return None

def create_thumbnail(image_path, thumb_path, size=(600, 600)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(thumb_path, "JPEG", optimize=True, quality=80)
            return True
    except Exception as e:
        print(f"Error creating thumbnail for {image_path}: {e}")
        return False

class Indexer:
    def __init__(self, root_dir=PHOTO_FOLDER):
        self.root_dir = Path(root_dir)
        self.model = None
        self.index = None
        self.image_ids = [] # To map FAISS index back to DB IDs (1-indexed?)
        
        # Load existing FAISS index if available
        if INDEX_PATH.exists():
            print(f"Loading existing index from {INDEX_PATH}")
            self.index = faiss.read_index(str(INDEX_PATH))
        
        # But wait, FAISS index indices are consecutive integers 0..N.
        # We need to map FAISS ID -> DB ID.
        # We can store this mapping in a separate file, or just rely on DB order if we rebuild every time? 
        # Rebuilding every time or keeping a mapping file is safer.
        # For this prototype, to support incremental updates properly, we might need a mapping.
        # BUT, if we use `IndexIDMap`, we can store arbitrary IDs.
        # Let's use IndexFlatIP with IDMap.
        
        if self.index is None:
             # Dimension for CLIP ViT-B-32 is 512
            d = 512 
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(d))

    def load_model(self):
        if self.model is None:
            print(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
            self.model = SentenceTransformer(CLIP_MODEL_NAME)
            print("Model loaded.")

    def scan_files(self):
        print(f"Scanning files in {self.root_dir}...")
        found_files = {}
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if Path(file).suffix.lower() in IMAGE_EXTS:
                    full_path = str(Path(root) / file)
                    found_files[full_path] = os.path.getmtime(full_path)
        return found_files

    def run(self, force_reindex=False):
        init_db()
        
        # Get existing state
        db_images = get_all_images_map() # path -> {id, mtime, file_hash}
        disk_files = self.scan_files()   # path -> mtime
        
        to_add = []
        to_update = []
        to_delete = []

        # Detect Deleted
        for path, meta in db_images.items():
            if path not in disk_files:
                to_delete.append(meta['id'])

        # Detect New or Changed
        for path, mtime in disk_files.items():
            if path not in db_images:
                to_add.append(path)
            else:
                # Check mtime first (fast)
                if abs(mtime - db_images[path]['mtime']) > 1.0 or force_reindex:
                     to_update.append(path)
        
        print(f"Found {len(to_add)} new, {len(to_update)} changed, {len(to_delete)} deleted images.")

        if not (to_add or to_update or to_delete):
            print("No changes detected.")
            return

        # Load Model only if needed
        if to_add or to_update:
            self.load_model()

        # Handle Deletions
        if to_delete:
            print(f"Removing {len(to_delete)} images...")
            # Remove from DB
            for img_id in to_delete:
                delete_image(img_id)
            # Remove from FAISS
            # FAISS IndexIDMap supports remove_ids
            self.index.remove_ids(np.array(to_delete, dtype=np.int64))

        # Process New/Updated
        process_list = to_add + to_update
        total = len(process_list)
        
        for i, path in enumerate(process_list):
            print(f"[{i+1}/{total}] Processing {path}")
            
            try:
                # 1. Metadata
                stat = os.stat(path)
                file_hash = calculate_file_hash(path)
                exif_date = get_exif_date(path)
                img_obj = Image.open(path)
                width, height = img_obj.size
                
                # 2. Thumbnail
                rel_path = hashlib.md5(path.encode()).hexdigest() + ".jpg"
                thumb_path = THUMBNAILS_DIR / rel_path
                create_thumbnail(path, thumb_path)
                
                # 3. Embedding
                # Image.open is lazy, need to ensure it's loaded for CLIP
                # sentence-transformers handles loading from path string usually, or PIL image
                embedding = self.model.encode(img_obj)
                embedding = embedding.astype('float32')
                # Normalize for Cosine Similarity (IndexFlatIP)
                faiss.normalize_L2(embedding.reshape(1, -1))
                
                # 4. Save to DB
                meta = {
                    'file_path': path,
                    'filename': os.path.basename(path),
                    'folder': os.path.dirname(path),
                    'mtime': stat.st_mtime,
                    'file_hash': file_hash,
                    'exif_date': exif_date,
                    'width': width,
                    'height': height,
                    'thumbnail_path': rel_path
                }
                img_id = upsert_image(meta)
                
                # 5. Update Index
                # If updating, remove old vector first if strictly needed, but IDMap replace might not exist?
                # FAISS IDMap doesn't support update well without remove first?
                # "add_with_ids" will add. If ID exists, multiple vectors per ID? 
                # Yes, standard IndexIDMap allows multiple vectors for same ID. 
                # So we should remove first if it's an update.
                
                if path in to_update:
                     # Find ID from DB map (we have it)
                     old_id = db_images[path]['id']
                     self.index.remove_ids(np.array([old_id], dtype=np.int64))
                     # We use same ID? upsert_image returns ID. 
                     # If we used replace in sqlite, ID might change? No, we used UPDATE. ID stays.
                     # So img_id should be same as old_id.
                
                self.index.add_with_ids(
                    embedding.reshape(1, -1), 
                    np.array([img_id], dtype=np.int64)
                )

            except Exception as e:
                print(f"Failed to process {path}: {e}")
                continue

        # Save Index
        print(f"Saving index to {INDEX_PATH}...")
        faiss.write_index(self.index, str(INDEX_PATH))
        print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Force reindex changed files")
    args = parser.parse_args()
    
    idx = Indexer()
    idx.run(force_reindex=args.reindex)
