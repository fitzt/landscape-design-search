import os
import numpy as np
from PIL import Image
from collections import defaultdict
import hashlib

def get_visual_hash(image_path, size=(32, 32)):
    """Creates a very simple visual hash by resizing and grayscaling."""
    try:
        with Image.open(image_path) as img:
            img = img.convert('L').resize(size, Image.Resampling.LANCZOS)
            data = np.asarray(img)
            # Normalize and return a hash of the pixel data
            return hashlib.md5(data.tobytes()).hexdigest()
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def deep_dedupe(directory):
    print(f"Running deep visual deduplication in {directory}...")
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.webp', '.jpg', '.jpeg', '.png'))]
    
    visual_hashes = defaultdict(list)
    processed = 0
    
    for f in files:
        path = os.path.join(directory, f)
        v_hash = get_visual_hash(path)
        if v_hash:
            visual_hashes[v_hash].append(f)
        processed += 1
        if processed % 50 == 0:
            print(f"Processed {processed}/{len(files)} images...")
            
    duplicates_found = 0
    total_reclaimed = 0
    
    for v_hash, file_list in visual_hashes.items():
        if len(file_list) > 1:
            # Sort by length, then name (keep shortest/cleanest)
            file_list.sort(key=lambda x: (len(x), x))
            keep = file_list[0]
            dups = file_list[1:]
            
            print(f"\n[Visual Match] Found {len(file_list)} similar images:")
            print(f"  KEEP: {keep}")
            for d in dups:
                d_path = os.path.join(directory, d)
                size = os.path.getsize(d_path)
                print(f"  DELETE: {d} ({size/1024:.1f} KB)")
                # os.remove(d_path) # Uncomment after verification
                duplicates_found += 1
                total_reclaimed += size
                
    print("\n" + "="*50)
    print(f"Visual Scan Complete.")
    print(f"Potential visual duplicates found: {duplicates_found}")
    print(f"Potential space savings: {total_reclaimed/(1024*1024):.2f} MB")
    print("NOTE: No files were actually deleted. Verification required.")

if __name__ == "__main__":
    TARGET_DIR = "/Users/thomasfitzgerald/landscape-design-search-leahy/optimized_images"
    deep_dedupe(TARGET_DIR)
