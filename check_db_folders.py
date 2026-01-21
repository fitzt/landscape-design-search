import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def check_folders():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT folder, count(*) FROM images GROUP BY folder")
    rows = cur.fetchall()
    print("Image counts by folder in Postgres:")
    for folder, count in rows:
        print(f" - {folder}: {count}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_folders()
