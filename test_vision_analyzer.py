"""
Test script for vision analyzer
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.vision_analyzer import get_analyzer
from backend.db import get_db_connection

# Get a sample of image IDs
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT id FROM images WHERE tags IS NOT NULL LIMIT 12")
sample_ids = [row[0] for row in cur.fetchall()]
conn.close()

print(f"Testing with {len(sample_ids)} images: {sample_ids}")
print("=" * 80)

# Run analysis
analyzer = get_analyzer()
result = analyzer.analyze_vision_board(sample_ids)

# Print results
print("\n📊 VISION ANALYSIS RESULTS")
print("=" * 80)

print(f"\nTotal Images: {result['total_images']}")
print(f"Tag Diversity: {result['tag_diversity']} unique tags")
print(f"Avg Tags/Image: {result['avg_tags_per_image']}")

print("\n🎨 THEMES:")
for i, theme in enumerate(result['themes'], 1):
    print(f"\n{i}. {theme['name']} ({theme['confidence']*100:.0f}% confidence)")
    print(f"   Images: {theme['image_count']}")
    print(f"   Top Tags: {', '.join(theme['top_tags'][:3])}")

print("\n🏷️  TOP ELEMENTS:")
for elem in result['top_elements'][:8]:
    print(f"  • {elem['label']}: {elem['count']}/{result['total_images']} images ({elem['percentage']:.0f}%)")

if result.get('materials'):
    print(f"\n🪨 MATERIALS: {', '.join(result['materials'])}")

if result.get('planting_signals'):
    print(f"\n🌿 PLANTING: {', '.join(result['planting_signals'])}")

if result.get('layout_preference'):
    print(f"\n📐 LAYOUT: {result['layout_preference']}")

if result.get('maintenance_vibe'):
    print(f"\n🛠️  MAINTENANCE: {result['maintenance_vibe']}")

print("\n💡 KEY INSIGHTS:")
for insight in result['unconscious_patterns']:
    print(f"  - {insight}")

print("\n" + "=" * 80)
print("📄 SALES BRIEF:")
print("=" * 80)
print(result['sales_brief'])
