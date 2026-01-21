import os
import numpy as np
from PIL import Image
from difflib import SequenceMatcher

def get_image_data(path, size=(16, 16)):
    try:
        with Image.open(path) as img:
            img = img.convert('L').resize(size, Image.Resampling.LANCZOS)
            return np.array(img, dtype=float)
    except Exception as e:
        return None

def filename_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def deep_scan(directory, threshold=0.9):
    print(f"Deep scanning {directory} for visual duplicates...")
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.webp', '.jpg', '.jpeg', '.png'))]
    files.sort()
    
    # 1. Group by dimensions (fast filter)
    dims_map = {}
    for f in files:
        path = os.path.join(directory, f)
        try:
            with Image.open(path) as img:
                d = img.size
                if d not in dims_map: dims_map[d] = []
                dims_map[d].append(f)
        except: continue
        
    dupes = []
    
    # 2. Within each dimension group, check visual similarity
    for dim, group in dims_map.items():
        if len(group) < 2: continue
        
        print(f"Checking group with dimensions {dim} ({len(group)} files)...")
        # Pre-load image data
        data_map = {}
        for f in group:
            data = get_image_data(os.path.join(directory, f))
            if data is not None:
                data_map[f] = data
                
        sub_group = list(data_map.keys())
        for i in range(len(sub_group)):
            for j in range(i + 1, len(sub_group)):
                f1, f2 = sub_group[i], sub_group[j]
                
                # Check filename similarity first as a hint
                f_sim = filename_similarity(f1, f2)
                
                # Calculate MSE (Mean Squared Error)
                d1, d2 = data_map[f1], data_map[f2]
                mse = np.mean((d1 - d2) ** 2)
                
                # Very low MSE = high similarity
                # For 16x16, MSE < 5.0 is extremely similar
                if mse < 5.0 or (mse < 50.0 and f_sim > 0.8):
                    dupes.append((mse, f1, f2))
                    print(f"  [Match] MSE: {mse:.2f}, Filename Sim: {f_sim:.2f}")
                    print(f"    {f1} <-> {f2}")

    if not dupes:
        print("No visual duplicates found with current thresholds.")
        return

    print("\n" + "="*50)
    print(f"Deep Scan Summary: Found {len(dupes)} candidates.")
    
    # Actually delete if MSE is very low (e.g. < 1.0) or (MSE < 10.0 and high filename sim)
    deleted_count = 0
    reclaimed = 0
    for mse, f1, f2 in dupes:
        # Keep shorter filename
        candidates = [f1, f2]
        candidates.sort(key=lambda x: (len(x), x))
        keep, delete = candidates[0], candidates[1]
        
        del_path = os.path.join(directory, delete)
        if os.path.exists(del_path):
            size = os.path.getsize(del_path)
            print(f"Deleting {delete} (MSE: {mse:.2f})")
            os.remove(del_path)
            deleted_count += 1
            reclaimed += size
            
    print(f"Deleted {deleted_count} visual duplicates.")
    print(f"Reclaimed {reclaimed/(1024*1024):.2f} MB.")

if __name__ == "__main__":
    deep_scan("/Users/thomasfitzgerald/landscape-design-search-leahy/optimized_images")
