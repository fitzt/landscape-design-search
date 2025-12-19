"""
Database migration to add AI tagging columns to images table.
Run this script once to add: tags (JSONB), caption (TEXT), style_scores (JSONB)
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    """Add columns for AI-generated tags and metadata."""
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        print("Adding AI tagging columns to images table...")
        
        # Add tags column (JSONB for structured tag data)
        cur.execute("""
            ALTER TABLE images 
            ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
        """)
        print("✓ Added 'tags' column")
        
        # Add caption column (AI-generated description)
        cur.execute("""
            ALTER TABLE images 
            ADD COLUMN IF NOT EXISTS caption TEXT;
        """)
        print("✓ Added 'caption' column")
        
        # Add style_scores column (confidence scores for each tag)
        cur.execute("""
            ALTER TABLE images 
            ADD COLUMN IF NOT EXISTS style_scores JSONB DEFAULT '{}'::jsonb;
        """)
        print("✓ Added 'style_scores' column")
        
        # Create index on tags for faster queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_tags 
            ON images USING GIN (tags);
        """)
        print("✓ Created GIN index on tags")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("AI Vision Analysis - Database Migration")
    print("=" * 60)
    print()
    
    response = input("This will modify the images table. Continue? (yes/no): ")
    if response.lower() == 'yes':
        run_migration()
    else:
        print("Migration cancelled.")
