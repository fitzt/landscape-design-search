import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def inspect_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'images'
        ORDER BY ordinal_position;
    """)
    rows = cur.fetchall()
    print("Postgres 'images' table columns:")
    for row in rows:
        print(f" - {row[0]} ({row[1]})")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect_schema()
