#!/bin/bash

# Process Leahy Photos Script
# Run this after uploading photos to optimized_images/

set -e

LEAHY_DIR="/Users/thomasfitzgerald/landscape-design-search-leahy"

echo "🖼️  Processing Leahy Landscaping photos..."
echo ""

cd "$LEAHY_DIR"

# Check if photos exist
PHOTO_COUNT=$(find optimized_images -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) 2>/dev/null | wc -l | xargs)

if [ "$PHOTO_COUNT" -eq 0 ]; then
    echo "❌ No photos found in optimized_images/"
    echo "   Please upload your photos first:"
    echo "   $LEAHY_DIR/optimized_images/"
    exit 1
fi

echo "📸 Found $PHOTO_COUNT photos to process"
echo ""

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Run indexer
echo "🔍 Running indexer (this may take a while)..."
python3 backend/indexer.py --reindex

echo ""
echo "✅ Processing complete!"
echo ""
echo "📊 Summary:"
echo "   - Photos indexed: $PHOTO_COUNT"
echo "   - Database: landscape.db"
echo "   - Search index: faiss_index.bin"
echo ""
echo "🚀 Start the Leahy server:"
echo "   cd $LEAHY_DIR"
echo "   source venv/bin/activate"
echo "   uvicorn backend.app:app --reload --port 8001"
echo ""
echo "🌐 Access at: http://localhost:8001"
echo ""
