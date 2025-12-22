import os
import asyncio
import json
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import psycopg2
from openai import AsyncOpenAI
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# OpenAI Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PROMPT = (
    "As an expert Landscape Architect, analyze this professional property photograph. "
    "Provide a JSON response with terms characterizing the design. "
    "Include the following arrays and fields using professional industry vocabulary:\n"
    "1. rich_tags: (array of strings) 15 descriptive design adjectives.\n"
    "2. hardscape_materials: (array of strings) specific stone, wood, masonry types.\n"
    "3. softscape_elements: (array of strings) plant varieties, horticultural styles.\n"
    "4. architectural_features: (array of strings) structures, water, fire features.\n"
    "5. design_style: (string) overall aesthetic (e.g. Modern, English Cottage, Minimalist).\n"
    "6. lighting_atmosphere: (string) quality of light and mood.\n"
    "7. maintenance_level: (string) expected care requirements.\n"
    "8. seasonal_interest: (string) peak performative seasons.\n"
    "9. spatial_purpose: (string) primary human function of the space.\n"
    "10. color_palette: (array of strings) key color themes detected.\n"
    "11. privacy_level: (string) 'Secluded' (high hedges/walls), 'Semi-Private' (some screening), 'Open Vista' (wide horizons).\n"
    "12. terrain_type: (string) 'Flat' (continuous grade), 'Terraced' (multiple levels/steps), 'Sloped' (angled grade).\n"
    "13. hardscape_ratio: (string) 'Hardscape Dominant', 'Balanced', or 'Softscape Dominant'.\n"
    "14. material_palette: (array of strings) Specific nouns for surfacing and structure (e.g., 'Bluestone', 'Corten Steel', 'Ipe Decking', 'River Rock', 'Cedar').\n"
    "No people are in these photos."
)

async def enrich_image(image_id: int, image_url: str):
    """Enrich a single image using GPT-4o-vision."""
    logger.info(f"Enriching image {image_id}: {image_url}")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        choice = response.choices[0]
        analysis_str = choice.message.content
        finish_reason = choice.finish_reason
        refusal = getattr(choice.message, 'refusal', None)

        if not analysis_str:
            logger.error(f"Empty content from AI for image {image_id}. Reason: {finish_reason}, Refusal: {refusal}")
            # Mark as refused to avoid re-scanning
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("UPDATE public.images SET design_style = %s WHERE id = %s", ('[Refused by AI]', image_id))
            conn.commit()
            cur.close()
            conn.close()
            return

        logger.debug(f"AI response for {image_id}: {analysis_str}")
        
        # Defensive JSON parsing
        if analysis_str.startswith("```json"):
            analysis_str = analysis_str.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(analysis_str)
        
        # Use psycopg2 for reliable array updates
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        sql = """
            UPDATE public.images 
            SET 
                rich_tags = %s,
                hardscape_materials = %s,
                softscape_elements = %s,
                architectural_features = %s,
                design_style = %s,
                lighting_atmosphere = %s,
                maintenance_level = %s,
                seasonal_interest = %s,
                spatial_purpose = %s,
                color_palette = %s,
                privacy_level = %s,
                terrain_type = %s,
                hardscape_ratio = %s,
                material_palette = %s
            WHERE id = %s
        """
        
        cur.execute(sql, (
            analysis.get("rich_tags", []),
            analysis.get("hardscape_materials", []),
            analysis.get("softscape_elements", []),
            analysis.get("architectural_features", []),
            analysis.get("design_style"),
            analysis.get("lighting_atmosphere"),
            analysis.get("maintenance_level"),
            analysis.get("seasonal_interest"),
            analysis.get("spatial_purpose"),
            analysis.get("color_palette", []),
            analysis.get("privacy_level"),
            analysis.get("terrain_type"),
            analysis.get("hardscape_ratio"),
            analysis.get("material_palette", []),
            image_id
        ))
        
        conn.commit()
        if cur.rowcount > 0:
            logger.info(f"Successfully enriched image {image_id}: {analysis.get('privacy_level')}, {analysis.get('hardscape_ratio')}")
        else:
            logger.error(f"Failed to find image {image_id} for update")
            
        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error enriching image {image_id}: {str(e)}")

async def main():
    # 1. Fetch images missing site intelligence data
    res = supabase.table("images").select("id, file_path").is_("privacy_level", "null").order("id").execute()
    
    images = res.data
    logger.info(f"Found {len(images)} images to enrich")
    
    if not images:
        return

    # 2. Process in batches
    batch_size = 5
    for i in range(0, len(images), batch_size):
        batch = images[i:i + batch_size]
        tasks = [enrich_image(img["id"], img["file_path"]) for img in batch]
        await asyncio.gather(*tasks)
        logger.info(f"Completed batch {i//batch_size + 1}")

if __name__ == "__main__":
    asyncio.run(main())
