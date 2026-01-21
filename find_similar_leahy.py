import os
from difflib import SequenceMatcher
from collections import defaultdict

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def find_similar_files(directory, threshold=0.8):
    print(f"Checking for similar filenames in {directory} (threshold: {threshold})...")
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and not f.startswith('.')]
    files.sort()
    
    similar_pairs = []
    
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            sim = similarity(files[i], files[j])
            if sim >= threshold:
                similar_pairs.append((sim, files[i], files[j]))
    
    # Sort by similarity descending
    similar_pairs.sort(key=lambda x: x[0], reverse=True)
    
    if not similar_pairs:
        print("No similar filenames found.")
        return

    print(f"Found {len(similar_pairs)} pairs with similarity >= {threshold}:")
    for sim, f1, f2 in similar_pairs[:20]: # Show top 20
        print(f"[{sim:.2f}] {f1} <-> {f2}")
        
    return similar_pairs

if __name__ == "__main__":
    import sys
    TARGET_DIR = "/Users/thomasfitzgerald/landscape-design-search-leahy/optimized_images"
    if len(sys.argv) > 1:
        TARGET_DIR = sys.argv[1]
    
    find_similar_files(TARGET_DIR)
