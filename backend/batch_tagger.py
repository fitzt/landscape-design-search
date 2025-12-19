"""
Batch tagger for landscape portfolio images.
Uses CLIP zero-shot classification to tag all images with controlled taxonomy.
Runs once (or incrementally) to populate tags, captions, and style scores.
"""

import os
import sys
from pathlib import Path
import json
from PIL import Image
import numpy as np
from sentence_transformers import SentenceTransformer, util
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.taxonomy import TAXONOMY, ALL_TAGS, get_tag_label
from backend.config import CLIP_MODEL_NAME
from backend.db import get_db_connection

class BatchTagger:
    def __init__(self):
        print(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
        self.model = SentenceTransformer(CLIP_MODEL_NAME)
        print("✓ Model loaded")
        
        # Precompute tag embeddings (do this once)
        print("Encoding taxonomy tags...")
        self.tag_embeddings = {}
        for category, tags in TAXONOMY.items():
            # Create natural language prompts for better classification
            prompts = [f"a landscape photo featuring {get_tag_label(tag)}" for tag in tags]
            embeddings = self.model.encode(prompts, convert_to_tensor=True)
            for tag, emb in zip(tags, embeddings):
                self.tag_embeddings[tag] = emb
        print(f"✓ Encoded {len(self.tag_embeddings)} tags")
    
    def tag_image(self, image_path: str, top_k: int = 5, threshold: float = 0.25):
        """
        Tag a single image using zero-shot classification.
        
        Args:
            image_path: Path to image file
            top_k: Number of top tags to return per category
            threshold: Minimum similarity score (0-1)
        
        Returns:
            dict with 'tags', 'caption', 'style_scores'
        """
        try:
            # Load and encode image
            image = Image.open(image_path)
            img_emb = self.model.encode(image, convert_to_tensor=True)
            
            # Calculate similarities for all tags
            tag_scores = {}
            for tag, tag_emb in self.tag_embeddings.items():
                similarity = float(util.cos_sim(img_emb, tag_emb)[0][0])
                if similarity >= threshold:
                    tag_scores[tag] = similarity
            
            # Sort by score and take top tags
            sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Build result
            selected_tags = []
            style_scores = {}
            
            # Take top tags per category to ensure diversity
            from backend.taxonomy import TAG_TO_CATEGORY
            category_counts = {}
            
            for tag, score in sorted_tags:
                category = TAG_TO_CATEGORY.get(tag, "unknown")
                
                # Limit tags per category to avoid over-representation
                if category_counts.get(category, 0) < 3:
                    selected_tags.append(tag)
                    style_scores[tag] = round(score, 3)
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                if len(selected_tags) >= top_k * 2:  # Max ~10 tags total
                    break
            
            # Generate caption from top tags
            top_labels = [get_tag_label(tag) for tag in selected_tags[:5]]
            caption = f"Landscape featuring {', '.join(top_labels[:3])}"
            if len(top_labels) > 3:
                caption += f" with {' and '.join(top_labels[3:])}"
            
            return {
                "tags": selected_tags,
                "caption": caption,
                "style_scores": style_scores
            }
            
        except Exception as e:
            print(f"Error tagging {image_path}: {e}")
            return {"tags": [], "caption": "", "style_scores": {}}
    
    def batch_tag_all(self, limit: int = None, resume: bool = True):
        """
        Tag all images in the database.
        
        Args:
            limit: Max number of images to process (None = all)
            resume: Skip images that already have tags
        """
        conn = get_db_connection()
        
        # Get images to process
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if resume:
                query = "SELECT id, file_path FROM images WHERE tags IS NULL OR tags = '[]'::jsonb"
            else:
                query = "SELECT id, file_path FROM images"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            images = cur.fetchall()
        
        print(f"\n{'='*60}")
        print(f"Batch Tagging: {len(images)} images")
        print(f"{'='*60}\n")
        
        success_count = 0
        error_count = 0
        
        for img in tqdm(images, desc="Tagging images"):
            img_id = img['id']
            file_path = img['file_path']
            
            if not os.path.exists(file_path):
                error_count += 1
                continue
            
            # Tag the image
            result = self.tag_image(file_path)
            
            # Update database
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE images 
                        SET tags = %s::jsonb,
                            caption = %s,
                            style_scores = %s::jsonb
                        WHERE id = %s
                    """, (
                        json.dumps(result['tags']),
                        result['caption'],
                        json.dumps(result['style_scores']),
                        img_id
                    ))
                conn.commit()
                success_count += 1
                
            except Exception as e:
                print(f"\nDB Error for image {img_id}: {e}")
                conn.rollback()
                error_count += 1
        
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"Batch Tagging Complete!")
        print(f"✓ Success: {success_count}")
        print(f"✗ Errors: {error_count}")
        print(f"{'='*60}\n")

def main():
    load_dotenv()
    
    import argparse
    parser = argparse.ArgumentParser(description="Batch tag landscape images")
    parser.add_argument('--limit', type=int, help='Max images to process')
    parser.add_argument('--no-resume', action='store_true', help='Re-tag all images')
    parser.add_argument('--test', action='store_true', help='Test mode (10 images)')
    
    args = parser.parse_args()
    
    tagger = BatchTagger()
    
    if args.test:
        print("🧪 TEST MODE: Processing 10 images")
        tagger.batch_tag_all(limit=10, resume=True)
    else:
        tagger.batch_tag_all(
            limit=args.limit,
            resume=not args.no_resume
        )

if __name__ == "__main__":
    main()
