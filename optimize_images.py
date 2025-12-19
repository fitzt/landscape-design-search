import os
import sys
from PIL import Image

def optimize_images(source_path, dest_dir):
    """
    Recursively finds images in source_path, resizes them (max 1920x1080),
    converts to JPG (80% quality), and saves to dest_dir.
    Handles duplicate filenames by appending a counter.
    """
    
    if not os.path.exists(source_path):
        print(f"Error: Source path does not exist: {source_path}")
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        print(f"Created destination directory: {dest_dir}")

    # Supported extensions
    valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.bmp'}
    
    count = 0
    errors = 0
    skipped = 0
    
    print(f"Starting optimized scan...")
    print(f"Source: {source_path}")
    print(f"Destination: {dest_dir}")
    print("-" * 50)

    for root, dirs, files in os.walk(source_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in valid_extensions:
                continue

            file_path = os.path.join(root, file)
            
            try:
                with Image.open(file_path) as img:
                    # Convert to RGB (essential for PNG/TIFF to JPG)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize while maintaining aspect ratio
                    img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    
                    # Generate filename
                    base_name = os.path.splitext(file)[0]
                    # Clean filename slightly if needed (optional, but good practice)
                    # base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                    
                    new_filename = f"{base_name}.jpg"
                    dest_path = os.path.join(dest_dir, new_filename)
                    
                    # Handle duplicates
                    dup_count = 1
                    while os.path.exists(dest_path):
                        new_filename = f"{base_name}_{dup_count}.jpg"
                        dest_path = os.path.join(dest_dir, new_filename)
                        dup_count += 1
                    
                    # Save
                    img.save(dest_path, "JPEG", quality=80, optimize=True)
                    
                    count += 1
                    if count % 20 == 0:
                        print(f"Processed {count} images...")
                        
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                errors += 1

    print("-" * 50)
    print(f"Finished.")
    print(f"Total processed: {count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    # Hardcoded paths as per request
    SOURCE_PATH = "/Users/thomasfitzgerald/Library/CloudStorage/GoogleDrive-tom@lynchlandscape.com/.shortcut-targets-by-id/1ZEUjPbtmKpAm9L2tlgKTNWKaZRISgwJp/Portfolio Photos"
    DEST_DIR = "./optimized_images"
    
    # Optional: Allow CLI override
    if len(sys.argv) > 1:
        SOURCE_PATH = sys.argv[1]
    if len(sys.argv) > 2:
        DEST_DIR = sys.argv[2]

    # Ensure absolute path for destination if relative provided
    DEST_DIR = os.path.abspath(DEST_DIR)

    optimize_images(SOURCE_PATH, DEST_DIR)
