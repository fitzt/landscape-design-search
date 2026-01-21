import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        migration_path = "/Users/thomasfitzgerald/landscape-design-search/enable_rls_projects.sql"
        with open(migration_path, "r") as f:
            sql = f.read()
            
        print("Running RLS Migration for Projects...")
        cur.execute(sql)
        conn.commit()
        print("Migration completed successfully. RLS enabled.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
