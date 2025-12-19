import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()
cur.execute("SELECT id, vision_json FROM leads ORDER BY id DESC LIMIT 1")
row = cur.fetchone()
if row:
    print(f"Lead ID: {row[0]}")
    print("Vision JSON:")
    print(json.dumps(row[1], indent=2))
else:
    print("No leads found.")
conn.close()
