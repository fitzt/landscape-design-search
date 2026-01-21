import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_leahy_seeds():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id, filename FROM images WHERE project_slug = 'leahy' LIMIT 8")
    rows = cur.fetchall()
    print("Potential Leahy Seeds:")
    for row in rows:
        print(f"{{ id: {row[0]}, label: '{row[1]}' }},")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_leahy_seeds()
