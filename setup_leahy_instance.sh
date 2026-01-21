#!/bin/bash

# Setup Script for Leahy Landscaping Instance
# Creates a completely separate instance of the landscape-design-search app

set -e  # Exit on any error

echo "🚀 Setting up Leahy Landscaping instance..."
echo ""

# Define paths
SOURCE_DIR="/Users/thomasfitzgerald/landscape-design-search"
LEAHY_DIR="/Users/thomasfitzgerald/landscape-design-search-leahy"
MODEL_FILE="sam_vit_b_01ec64.pth"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: Source directory $SOURCE_DIR not found"
    exit 1
fi

# Check if Leahy directory already exists
if [ -d "$LEAHY_DIR" ]; then
    echo "⚠️  Warning: $LEAHY_DIR already exists"
    read -p "Do you want to delete it and start fresh? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing Leahy instance..."
        rm -rf "$LEAHY_DIR"
    else
        echo "❌ Aborted. Please remove $LEAHY_DIR manually or choose a different name."
        exit 1
    fi
fi

echo "📁 Cloning project to Leahy instance..."
cp -R "$SOURCE_DIR" "$LEAHY_DIR"

echo "🧹 Cleaning up Leahy instance..."
cd "$LEAHY_DIR"

# Remove old virtual environment
rm -rf venv

# Remove old data files (we'll create fresh ones)
rm -f landscape.db
rm -f faiss_index.bin
rm -f *.log
rm -f images.csv

# Remove existing photos
rm -rf optimized_images/*

# Remove thumbnails
rm -rf backend/static/thumbnails/*

# Create fresh directories
mkdir -p optimized_images
mkdir -p backend/static/thumbnails

echo "🐍 Creating fresh virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Symlink the large model file to save space (375MB)
if [ -f "$SOURCE_DIR/$MODEL_FILE" ]; then
    echo "🔗 Creating symlink for model file (saves 375MB)..."
    # Remove the copied file if it exists
    if [ -f "$LEAHY_DIR/$MODEL_FILE" ]; then
        rm "$LEAHY_DIR/$MODEL_FILE"
    fi
    ln -s "$SOURCE_DIR/$MODEL_FILE" "$LEAHY_DIR/$MODEL_FILE"
    echo "   ✅ Symlinked $MODEL_FILE"
else
    echo "   ℹ️  Model file not found in source, will download when needed"
fi

echo ""
echo "✅ Leahy instance setup complete!"
echo ""
echo "📍 Location: $LEAHY_DIR"
echo ""
echo "📸 Next steps:"
echo "   1. Upload your 600 Leahy photos to:"
echo "      $LEAHY_DIR/optimized_images/"
echo ""
echo "   2. Process the photos:"
echo "      cd $LEAHY_DIR"
echo "      source venv/bin/activate"
echo "      python3 backend/indexer.py --reindex"
echo ""
echo "   3. Start the Leahy server (port 8001):"
echo "      uvicorn backend.app:app --reload --port 8001"
echo ""
echo "   4. Your original instance runs on port 8000:"
echo "      cd $SOURCE_DIR"
echo "      source venv/bin/activate"
echo "      uvicorn backend.app:app --reload --port 8000"
echo ""
