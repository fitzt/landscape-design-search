"""
Controlled taxonomy for landscape design image classification.
Defines 8 category groups with 40-80 total tags for consistent AI analysis.
"""

TAXONOMY = {
    "hardscape": [
        "large_format_pavers",
        "small_pavers", 
        "natural_stone",
        "bluestone",
        "concrete_pavers",
        "gravel",
        "decomposed_granite",
        "retaining_wall",
        "linear_steps",
        "curved_steps",
        "raised_beds",
        "metal_edging",
        "stone_edging",
    ],
    
    "structures": [
        "pergola",
        "fence",
        "privacy_screen",
        "seating_wall",
        "fire_pit",
        "outdoor_kitchen",
        "arbor",
        "trellis",
        "deck",
        "patio_cover",
    ],
    
    "lighting": [
        "uplighting",
        "path_lights",
        "string_lights",
        "step_lights",
        "accent_lighting",
        "moonlighting",
        "landscape_spotlights",
    ],
    
    "water_features": [
        "pondless_waterfall",
        "fountain",
        "reflecting_pool",
        "stream",
        "pond",
    ],
    
    "planting_style": [
        "formal",
        "naturalistic",
        "layered",
        "minimalist",
        "pollinator_friendly",
        "evergreen_heavy",
        "seasonal_color",
        "ornamental_grasses",
        "perennial_borders",
        "mass_planting",
        "mixed_borders",
    ],
    
    "maintenance_level": [
        "low_maintenance",
        "moderate_care",
        "high_detail_gardening",
    ],
    
    "layout": [
        "courtyard",
        "patio_centric",
        "meandering_path",
        "strong_axis",
        "terracing",
        "enclosed_space",
        "open_lawn",
        "garden_rooms",
    ],
    
    "materials": [
        "wood_heavy",
        "metal_accents",
        "dark_metal",
        "cedar",
        "black_aluminum",
        "warm_tones",
        "cool_tones",
    ],
    
    "style": [
        "modern_minimalist",
        "warm_modern",
        "traditional",
        "cottage_garden",
        "naturalistic",
        "formal",
        "rustic",
        "contemporary",
    ],
}

# Flattened list for easy iteration
ALL_TAGS = []
for category, tags in TAXONOMY.items():
    ALL_TAGS.extend(tags)

# Category lookup
TAG_TO_CATEGORY = {}
for category, tags in TAXONOMY.items():
    for tag in tags:
        TAG_TO_CATEGORY[tag] = category

# Human-readable labels
TAG_LABELS = {
    "large_format_pavers": "Large-Format Pavers",
    "small_pavers": "Small Pavers",
    "natural_stone": "Natural Stone",
    "bluestone": "Bluestone",
    "concrete_pavers": "Concrete Pavers",
    "gravel": "Gravel",
    "decomposed_granite": "Decomposed Granite",
    "retaining_wall": "Retaining Wall",
    "linear_steps": "Linear Steps",
    "curved_steps": "Curved Steps",
    "raised_beds": "Raised Beds",
    "metal_edging": "Metal Edging",
    "stone_edging": "Stone Edging",
    "pergola": "Pergola",
    "fence": "Fence",
    "privacy_screen": "Privacy Screen",
    "seating_wall": "Seating Wall",
    "fire_pit": "Fire Pit",
    "outdoor_kitchen": "Outdoor Kitchen",
    "arbor": "Arbor",
    "trellis": "Trellis",
    "deck": "Deck",
    "patio_cover": "Patio Cover",
    "uplighting": "Uplighting",
    "path_lights": "Path Lights",
    "string_lights": "String Lights",
    "step_lights": "Step Lights",
    "accent_lighting": "Accent Lighting",
    "moonlighting": "Moonlighting",
    "landscape_spotlights": "Landscape Spotlights",
    "pondless_waterfall": "Pondless Waterfall",
    "fountain": "Fountain",
    "reflecting_pool": "Reflecting Pool",
    "stream": "Stream",
    "pond": "Pond",
    "formal": "Formal",
    "naturalistic": "Naturalistic",
    "layered": "Layered Planting",
    "minimalist": "Minimalist",
    "pollinator_friendly": "Pollinator-Friendly",
    "evergreen_heavy": "Evergreen-Heavy",
    "seasonal_color": "Seasonal Color",
    "ornamental_grasses": "Ornamental Grasses",
    "perennial_borders": "Perennial Borders",
    "mass_planting": "Mass Planting",
    "mixed_borders": "Mixed Borders",
    "low_maintenance": "Low Maintenance",
    "moderate_care": "Moderate Care",
    "high_detail_gardening": "High-Detail Gardening",
    "courtyard": "Courtyard",
    "patio_centric": "Patio-Centric",
    "meandering_path": "Meandering Path",
    "strong_axis": "Strong Axis",
    "terracing": "Terracing",
    "enclosed_space": "Enclosed Space",
    "open_lawn": "Open Lawn",
    "garden_rooms": "Garden Rooms",
    "wood_heavy": "Wood-Heavy",
    "metal_accents": "Metal Accents",
    "dark_metal": "Dark Metal",
    "cedar": "Cedar",
    "black_aluminum": "Black Aluminum",
    "warm_tones": "Warm Tones",
    "cool_tones": "Cool Tones",
    "modern_minimalist": "Modern Minimalist",
    "warm_modern": "Warm Modern",
    "traditional": "Traditional",
    "cottage_garden": "Cottage Garden",
    "rustic": "Rustic",
    "contemporary": "Contemporary",
}

def get_tag_label(tag: str) -> str:
    """Get human-readable label for a tag."""
    return TAG_LABELS.get(tag, tag.replace("_", " ").title())

def get_category_tags(category: str) -> list:
    """Get all tags for a specific category."""
    return TAXONOMY.get(category, [])

def get_tag_category(tag: str) -> str:
    """Get the category for a specific tag."""
    return TAG_TO_CATEGORY.get(tag, "unknown")
