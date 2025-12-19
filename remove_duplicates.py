import os
import hashlib
from collections import defaultdict

def get_file_hash(filepath):
    """Calculates MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def remove_duplicates(directory):
    print(f"Scanning for duplicates in {directory}...")
    
    # Map hash -> list of filepaths
    hashes = defaultdict(list)
    files_checked = 0
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            file_hash = get_file_hash(filepath)
            hashes[file_hash].append(filepath)
            files_checked += 1
            if files_checked % 100 == 0:
                print(f"Checked {files_checked} files...")
    
    print(f"Scan complete. Found {len(hashes)} unique contents out of {files_checked} files.")
    
    deleted_count = 0
    saved_space = 0
    
    for file_hash, file_list in hashes.items():
        if len(file_list) > 1:
            # Sort files to find the "best" one to keep.
            # Strategy: Keep the one with the shortest filename (likely original), 
            # then alphabetical.
            # e.g. "image.jpg" vs "image_1.jpg" -> "image.jpg" is shorter.
            file_list.sort(key=lambda x: (len(os.path.basename(x)), os.path.basename(x)))
            
            keep = file_list[0]
            duplicates = file_list[1:]
            
            print(f"Keeping: {os.path.basename(keep)}")
            for dup in duplicates:
                print(f"  Deleting duplicate: {os.path.basename(dup)}")
                try:
                    size = os.path.getsize(dup)
                    os.remove(dup)
                    deleted_count += 1
                    saved_space += size
                except Exception as e:
                    print(f"  Error deleting {dup}: {e}")
    
    print("-" * 50)
    print(f"Deduplication complete.")
    print(f"Deleted {deleted_count} files.")
    print(f"Reclaimed {saved_space / (1024*1024):.2f} MB.")

if __name__ == "__main__":
    TARGET_DIR = "/Users/thomasfitzgerald/landscape-design-search/optimized_images"
    remove_duplicates(TARGET_DIR)
