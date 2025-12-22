import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def check_progress():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM images WHERE privacy_level IS NOT NULL")
    enriched_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM images")
    total_count = cur.fetchone()[0]
    
    print(f"Enriched: {enriched_count}")
    print(f"Total: {total_count}")
    print(f"Percentage: {(enriched_count/total_count)*100:.1f}%")
    
    # Sample data
    cur.execute("SELECT id, privacy_level, terrain_type, hardscape_ratio, material_palette FROM images WHERE privacy_level IS NOT NULL LIMIT 3")
    rows = cur.fetchall()
    for row in rows:
        print(f"ID {row[0]}: {row[1]}, {row[2]}, {row[3]}, {row[4]}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_progress()
