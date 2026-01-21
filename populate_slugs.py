import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def populate_slugs():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Updating project_slug for Lynch project...")
    cur.execute("""
        UPDATE images 
        SET project_slug = 'lynch' 
        WHERE folder LIKE '%/landscape-design-search/optimized_images'
    """)
    print(f" - Updated {cur.rowcount} rows for Lynch.")
    
    print("Updating project_slug for Leahy project...")
    cur.execute("""
        UPDATE images 
        SET project_slug = 'leahy' 
        WHERE folder LIKE '%/landscape-design-search-leahy/optimized_images'
    """)
    print(f" - Updated {cur.rowcount} rows for Leahy.")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Slug population complete.")

if __name__ == "__main__":
    populate_slugs()
