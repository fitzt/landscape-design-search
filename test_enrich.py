import asyncio
import os
from enrich_images import enrich_image, load_dotenv, logger
import psycopg2

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test_single():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    project_slug = os.getenv("PROJECT_SLUG")
    if project_slug:
        print(f"Test constrained to project: {project_slug}")
        cur.execute("SELECT id, file_path FROM images WHERE privacy_level IS NULL AND project_slug = %s LIMIT 1", (project_slug,))
    else:
        cur.execute("SELECT id, file_path FROM images WHERE privacy_level IS NULL LIMIT 1")
    row = cur.fetchone()
    conn.close()
    
    if row:
        img_id, path = row
        print(f"Testing enrichment for ID {img_id}: {path}")
        await enrich_image(img_id, path)
        print("Done.")
    else:
        print("No images found to enrich.")

if __name__ == "__main__":
    asyncio.run(test_single())
