import os
import cv2
import torch
import numpy as np
import psycopg2
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from transformers import CLIPProcessor, CLIPModel
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

# --- CONFIGURATION ---
BATCH_SIZE = 1  # Process one image fully (segment -> crop -> embed) at a time for memory safety
CLIP_CONFIDENCE_THRESHOLD = 0.6
CHECKPOINT_PATH = "sam_vit_b_01ec64.pth" # Must ensure this file exists or provide download link instructions
MODEL_TYPE = "vit_b"
# MPS has float64 issues with SAM AutomaticMaskGenerator, so we run SAM on CPU and CLIP on MPS
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
SAM_DEVICE = "cpu"

TARGET_OBJECTS = [
    # 1. Structural & Hardscape
    'Retaining Wall', 'Patio', 'Walkway', 'Steps', 'Pool Deck', 'Driveway', 
    'Fencing', 'Deck', 'Arbor', 'Pergola', 'Cabana', 'Gazebo', 'Pavilion', 
    'Trellis', 'Seat Wall', 'Stone Pier', 'Gate', 'Bridge',
    
    # 2. Masonry & Materials
    'Fireplace Masonry', 'Chimney', 'Stone Hearth', 'Decorative Stone', 
    'Boulders', 'Natural Stone', 'Bluestone', 'Pavers', 'Brick', 
    'Wood Decking', 'Composite Decking', 'Gravel', 'River Rock', 
    'Corten Steel', 'Glass Railing', 'Cobblestone', 'Fieldstone',
    
    # 3. Water Features & Pools
    'Swimming Pool', 'Infinity Edge', 'Waterfall', 'Fountain', 'Spa', 
    'Hot Tub', 'Bubbling Rock', 'Koi Pond', 'Pool Ladder', 'Diving Board',
    
    # 4. Amenities & High-End Details
    'Fire Pit', 'Outdoor Kitchen', 'Grill', 'Outdoor Sink', 'Pizza Oven', 
    'Outdoor Fridge', 'Kegerator', 'Bar Stool', 'Fire Table', 'TV', 
    'Outdoor Speakers', 'Outdoor Furniture', 'Patio Chair', 'Dining Table', 
    'Umbrella', 'Outdoor Rug', 'Hammock', 'Swing',
    
    # 5. Horticulture & Softscape
    'Hydrangea', 'Buxus Boxwood', 'Ornamental Grass', 'Lawn', 'Mulch',
    'Tree', 'Flower Bed', 'Container Plant', 'Arborvitae', 'Evergreen Tree',
    'Privacy Screening', 'Hedge', 'Japanese Maple', 'Perennials', 'Groundcover',
    
    # 6. Lighting
    'Outdoor Lighting', 'Path Light', 'String Lights', 'Sconce', 'Up-lighting'
]

# --- DB CONNECTION ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- MODELS ---
print(f"🚀 Initializing on DEVICE: {DEVICE}")

# 1. CLIP
print("Loading CLIP...")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 2. SAM
print("Loading SAM...")
if not os.path.exists(CHECKPOINT_PATH):
    print(f"⚠️  WARNING: Checkpoint {CHECKPOINT_PATH} not found. Analysis will likely fail.")

sam = sam_model_registry[MODEL_TYPE](checkpoint=CHECKPOINT_PATH)
sam.to(device=SAM_DEVICE)
mask_generator = SamAutomaticMaskGenerator(
    model=sam,
    points_per_side=32,
    pred_iou_thresh=0.86,
    stability_score_thresh=0.92,
    crop_n_layers=1,
    crop_n_points_downscale_factor=2,
    min_mask_region_area=100,  # Avoid tiny specks
)

def get_embedding(image_crop):
    """Generates a 512d vector for the cropped image using CLIP."""
    inputs = clip_processor(images=image_crop, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        image_features = clip_model.get_image_features(**inputs)
    return image_features.cpu().numpy().flatten().tolist()

def classify_crop(image_crop):
    """Classifies the crop against TARGET_OBJECTS using CLIP zero-shot."""
    inputs = clip_processor(text=TARGET_OBJECTS, images=image_crop, return_tensors="pt", padding=True).to(DEVICE)
    with torch.no_grad():
        outputs = clip_model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)  # softmax over classes
    
    # Get top prediction
    top_prob, top_idx = probs[0].topk(1)
    confidence = top_prob.item()
    label = TARGET_OBJECTS[top_idx.item()]
    
    return label, confidence

def process_image(image_id, image_path):
    print(f"Processing Image ID {image_id}: {image_path}")
    
    # 1. Load Image (Local or URL)
    image_np = None
    try:
        if image_path.startswith("http"):
            print(f"Downloading from URL: {image_path}")
            response = requests.get(image_path)
            response.raise_for_status()
            # Convert to numpy for SAM/CV2
            image_bytes = np.frombuffer(response.content, np.uint8)
            image_np = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
            if image_np is not None:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
        else:
            # Check local path
            actual_path = image_path
            if not os.path.exists(actual_path):
                # Try relative to static folder
                static_path = os.path.join("backend/static", image_path)
                if os.path.exists(static_path):
                    actual_path = static_path
                else:
                    print(f"❌ File not found: {image_path}")
                    return

            image_np = cv2.imread(actual_path)
            if image_np is not None:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)

        if image_np is None:
            print(f"❌ Could not load image: {image_path}")
            return

    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return

    # Use image_np for the rest of the function...
    image = image_np 

    # Generate Masks (SAM)
    print("  - Generating SAM masks...", end="", flush=True)
    masks = mask_generator.generate(image)
    print(f" Done. Found {len(masks)} masks.")

    objects_to_save = []
    
    # Analyze Channels (Crops)
    for i, mask_data in enumerate(masks):
        # mask_data['segmentation'] is binary mask
        # mask_data['bbox'] is [x, y, w, h]
        x, y, w, h = map(int, mask_data['bbox'])
        
        # Skip tiny crops
        if w < 50 or h < 50: 
            continue
            
        # Crop Image
        crop = image[y:y+h, x:x+w]
        pil_crop = Image.fromarray(crop)
        
        # CLIP Classification
        label, confidence = classify_crop(pil_crop)
        
        if confidence > CLIP_CONFIDENCE_THRESHOLD:
            # Generate Embedding
            embedding = get_embedding(pil_crop)
            
            # Prepare Polygon for DB (Simplified)
            # mask_data['segmentation'] is a boolean array. We need contours.
            # This can be heavy, let's keep it simple or skip distinct polygon logic for now if just bbox is enough.
            # User asked for mask_polygon (jsonb).
            # Convert binary mask to polygon
            # For efficiency in this script, we'll store bbox as a simple polygon or do a quick contour.
            # Let's do quick contour:
            
            # This mask is for the WHOLE image. We need to extract contours.
            binary_mask = mask_data['segmentation'].astype(np.uint8) * 255
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Take largest contour
                largest = max(contours, key=cv2.contourArea)
                # Simplify
                epsilon = 0.005 * cv2.arcLength(largest, True)
                approx = cv2.approxPolyDP(largest, epsilon, True)
                # Convert to list of [x, y]
                polygon_points = approx.reshape(-1, 2).tolist()
            else:
                polygon_points = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]] # Fallback to bbox
            
            print(f"    -> Found {label} ({confidence:.2f})")
            
            objects_to_save.append({
                'image_id': image_id,
                'label': label,
                'confidence': confidence,
                'mask_polygon': polygon_points, # Serialized as JSON automatically by psycopg2 if using json dump or adapter
                'object_embedding': embedding
            })

    # Batch Insert
    if objects_to_save:
        save_objects(image_id, objects_to_save)

def save_objects(image_id, objects):
    print(f"  - Saving {len(objects)} objects to DB (image {image_id})...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Clear previous objects
    try:
        cur.execute("DELETE FROM public.image_objects WHERE image_id = %s", (image_id,))
    except Exception as e:
        print(f"⚠️ Could not delete old objects: {e}")
        conn.rollback()
        cur = conn.cursor()

    sql = """
        INSERT INTO image_objects (image_id, label, confidence, mask_polygon, object_embedding)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    import json
    data = [
        (
            obj['image_id'], 
            obj['label'], 
            obj['confidence'], 
            json.dumps(obj['mask_polygon']), 
            obj['object_embedding']
        ) 
        for obj in objects
    ]
    
    try:
        cur.executemany(sql, data)
        conn.commit()
    except Exception as e:
        print(f"❌ DB Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch images that haven't been processed yet
    print(f"Fetching images for project: {os.getenv('PROJECT_SLUG', 'ALL')}...")
    
    sql = """
        SELECT i.id, i.file_path 
        FROM images i 
        WHERE NOT EXISTS (
            SELECT 1 FROM image_objects io WHERE io.image_id = i.id
        )
    """
    params = []
    
    project_slug = os.getenv("PROJECT_SLUG")
    if project_slug:
        sql += " AND i.project_slug = %s"
        params.append(project_slug)
        
    sql += " ORDER BY i.id DESC"
    
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"Found {len(rows)} images to process.")
    
    for row in rows:
        process_image(row[0], row[1])

if __name__ == "__main__":
    main()
