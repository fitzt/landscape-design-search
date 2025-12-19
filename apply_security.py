import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def apply_security():
    if not DATABASE_URL:
        print("DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Reading security script...")
        with open('apply_security.sql', 'r') as f:
            sql = f.read()
        
        print("Applying SQL policies...")
        # Split by semicolon to run individually, handling potential errors
        commands = sql.split(';')
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            try:
                print(f"Executing: {cmd[:50]}...")
                cur.execute(cmd)
            except Exception as e:
                print(f"Error executing command: {e}")
        
        conn.close()
        print("Security hardening applied successfully.")
    except Exception as e:
        print(f"Failed to connect or execute: {e}")

if __name__ == "__main__":
    apply_security()
