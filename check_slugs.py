import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def check_slugs():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT project_slug, count(*) FROM images GROUP BY project_slug")
    rows = cur.fetchall()
    print("Project Slugs in Postgres:")
    for slug, count in rows:
        print(f" - {slug}: {count}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_slugs()
