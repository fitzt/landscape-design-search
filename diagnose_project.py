import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def diagnose():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # 1. Total
    cur.execute("SELECT count(*) FROM images")
    total = cur.fetchone()[0]
    
    # 2. Local Tagging (BatchTagger)
    cur.execute("SELECT count(*) FROM images WHERE tags IS NOT NULL AND tags != '[]'::jsonb")
    tagged = cur.fetchone()[0]
    
    # 3. Local Object Detection (process_objects_m3)
    cur.execute("SELECT count(DISTINCT image_id) FROM image_objects")
    objectified = cur.fetchone()[0]
    
    # 4. Site Intelligence (enrich_images)
    cur.execute("SELECT count(*) FROM images WHERE privacy_level IS NOT NULL")
    enriched = cur.fetchone()[0]
    
    print(f"Project Enrichment Diagnostic:")
    print(f"================================")
    print(f"Total Images: {total}")
    print(f"Local Tags:   {tagged} ({tagged/total*100:.1f}%)")
    print(f"Local Objects: {objectified} ({objectified/total*100:.1f}%)")
    print(f"Site Intel:   {enriched} ({enriched/total*100:.1f}%)")
    print(f"================================")
    
    if total > 0:
        cur.execute("SELECT folder, count(*) FROM images GROUP BY folder")
        folders = cur.fetchall()
        for f, c in folders:
            print(f"Folder: {f} -> {c} images")

    cur.close()
    conn.close()

if __name__ == "__main__":
    diagnose()
