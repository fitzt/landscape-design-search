import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def create_projects_table():
    print(f"Connecting to {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Create Projects Table
    print("Creating projects table...")
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename_slug TEXT UNIQUE NOT NULL,
            display_title TEXT,
            location TEXT,
            description TEXT,
            awards TEXT[]
        )
    ''')

    # 2. Insert Seed Data
    print("Inserting seed data (mcgonigle)...")
    seed_sql = """
        INSERT INTO projects (filename_slug, display_title, location, description, awards)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (filename_slug) DO UPDATE 
        SET display_title = EXCLUDED.display_title,
            location = EXCLUDED.location,
            description = EXCLUDED.description,
            awards = EXCLUDED.awards;
    """
    
    awards = ['PRISM 2025 Gold – Best Outdoor Living', 'PRISM 2025 Silver – Best Outdoor Kitchen']
    description = (
        'This expansive Wayland property began as a blank canvas: a weed-strewn lawn bordering conservation land '
        'in a historic district. After navigating the conservation permitting process, our team transformed the '
        'grounds into an entertainer’s dream while preserving generous lawn space for the homeowners’ two energetic dogs. '
        'At the heart of the design is a large terraced patio that seamlessly accommodates gatherings of every scale. '
        'A fully equipped outdoor kitchen with ample counter and bar seating sets the stage for cocktail hour and meal prep. '
        'An open-air dining area invites guests to linger over gourmet meals, while a sunken firepit terrace extends the '
        'evening with intimate conversation. Thoughtfully designed planter walls provide subtle division and a sense of privacy, '
        'blending functionality with elegance. The homeowners were blown away with the final concept, and have happily reported '
        'they have been able to use the space in every season so far!'
    )
    
    cur.execute(seed_sql, ('lynch_landscape_mcgonigle_hr', 'Old Connecticut Path', 'Wayland, MA', description, awards))

    conn.commit()
    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    create_projects_table()
