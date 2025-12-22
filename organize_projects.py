import os
import psycopg2
import psycopg2.extras
import re
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_project_slug(file_path):
    if not file_path:
        return None
    
    # Get filename without extension
    filename = os.path.basename(file_path).rsplit('.', 1)[0]
    
    # Logic: Split on hyphens or underscores preceding numbers
    # Taking everything except the last numeric segment.
    # Example: mcgonigle_01 -> mcgonigle
    # Example: old-connecticut-path-003 -> old-connecticut-path
    
    # regex matches anything followed by a separator (- or _) and digits at the end
    match = re.match(r'^(.*)[-_]\d+$', filename)
    if match:
        slug = match.group(1).lower()
        # Safety: Must be at least 4 characters to avoid generic groupings
        if len(slug) >= 4:
            return slug
    
    return None

def organize_projects():
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Fetch all images
    print("Fetching images...")
    cur.execute("SELECT id, file_path FROM images")
    images = cur.fetchall()
    
    stats = {}
    updates = []
    
    print(f"Processing {len(images)} images...")
    for img in images:
        slug = get_project_slug(img['file_path'])
        if slug:
            updates.append((slug, img['id']))
            stats[slug] = stats.get(slug, 0) + 1
            
    # 2. Batch Update
    print(f"Updating {len(updates)} images with project slugs...")
    update_sql = "UPDATE images SET project_slug = %s WHERE id = %s"
    psycopg2.extras.execute_batch(cur, update_sql, updates)
    
    conn.commit()
    
    # 3. Log Summary
    print("\n--- Project Grouping Summary ---")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    for slug, count in sorted_stats:
        print(f"Project: {slug} | Count: {count}")
    
    print(f"\nTotal projects identified: {len(stats)}")
    print(f"Total images tagged: {len(updates)}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    organize_projects()
