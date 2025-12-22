import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def apply_migration():
    """Apply the enrichment expansion schema migration."""
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Executing expansion migration script...")
        with open("enrich_expansion.sql", "r") as f:
            sql = f.read()
            cur.execute(sql)
        
        conn.commit()
        print("Expansion migration applied successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error applying migration: {e}")

if __name__ == "__main__":
    apply_migration()
