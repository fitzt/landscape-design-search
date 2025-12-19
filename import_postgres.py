import psycopg2
import csv
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def  import_images():
    if not os.path.exists("images.csv"):
        print("images.csv not found.")
        return

    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Importing images.csv...")
    with open("images.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            # We need to handle potential NULLs or type conversion if necessary
            # SQLite dump is all strings.
            # Postgres fields: file_path, filename, folder, mtime, file_hash, exif_date, width, height, thumbnail_path, favorite, notes, created_at, updated_at
            
            # Helper to handle 'None' string or empty
            def val(k):
                v = row.get(k)
                if v == '' or v == 'None': return None
                return v

            cur.execute("""
                INSERT INTO images (
                    file_path, filename, folder, mtime, file_hash, exif_date, width, height, thumbnail_path, favorite, notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_path) DO NOTHING
            """, (
                val('file_path'), val('filename'), val('folder'), val('mtime'), val('file_hash'), 
                val('exif_date'), val('width'), val('height'), val('thumbnail_path'), 
                val('favorite'), val('notes'), val('created_at'), val('updated_at')
            ))
            count += 1
            if count % 100 == 0:
                print(f"Processed {count} rows...")
    
    conn.commit()
    conn.close()
    print(f"Import complete. Processed {count} rows.")

if __name__ == "__main__":
    import_images()
