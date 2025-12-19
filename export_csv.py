import sqlite3
import csv
import os
from backend.config import DB_PATH

def export_table_to_csv(table_name, cursor):
    print(f"Exporting {table_name}...")
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"No data in {table_name}")
        return

    # Get column names
    col_names = [description[0] for description in cursor.description]

    filename = f"{table_name}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(rows)
    print(f"Saved {filename}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    tables = ['images', 'collections', 'collection_items']
    
    for table in tables:
        export_table_to_csv(table, c)
        
    conn.close()
    print("Export complete.")

if __name__ == "__main__":
    main()
