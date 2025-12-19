import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def create_leads_table():
    if not DATABASE_URL:
        print("DATABASE_URL not set")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Creating leads table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            timeline TEXT,
            budget TEXT,
            address TEXT,
            vision_json JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Table leads created successfully.")

if __name__ == "__main__":
    create_leads_table()
