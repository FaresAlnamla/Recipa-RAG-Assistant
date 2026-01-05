#!/bin/bash
# Image Conversion Script - JPG/PNG to WebP
# This script converts all images in the public folder to WebP format
# Install cwebp first: brew install webp (macOS) or sudo apt-get install webp (Ubuntu)

echo "🖼️  Starting image conversion to WebP format..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if cwebp is installed
if ! command -v cwebp &> /dev/null; then
    echo -e "${RED}❌ cwebp is not installed${NC}"
    echo ""
    echo "Install it using:"
    echo "  macOS: brew install webp"
    echo "  Ubuntu: sudo apt-get install webp"
    echo "  Or download from: https://developers.google.com/speed/webp/download"
    exit 1
fi

echo "✅ cwebp found"
echo ""

# Navigate to public folder
cd "$(dirname "$0")/public" || exit

# Convert JPG files
echo -e "${YELLOW}Converting JPG files...${NC}"
for file in *.jpg; do
    if [ -f "$file" ]; then
        output="${file%.jpg}.webp"
        echo "  Converting: $file → $output"
        cwebp -q 85 -m 6 "$file" -o "$output"
        if [ $? -eq 0 ]; then
            # Get file sizes
            original_size=$(du -h "$file" | cut -f1)
            new_size=$(du -h "$output" | cut -f1)
            echo -e "    ${GREEN}✓ Done${NC} ($original_size → $new_size)"
        else
            echo -e "    ${RED}✗ Failed${NC}"
        fi
    fi
done

echo ""

# Convert PNG files (with higher quality)
echo -e "${YELLOW}Converting PNG files...${NC}"
for file in *.png; do
    if [ -f "$file" ]; then
        output="${file%.png}.webp"
        echo "  Converting: $file → $output"
        cwebp -q 90 -m 6 "$file" -o "$output"
        if [ $? -eq 0 ]; then
            original_size=$(du -h "$file" | cut -f1)
            new_size=$(du -h "$output" | cut -f1)
            echo -e "    ${GREEN}✓ Done${NC} ($original_size → $new_size)"
        else
            echo -e "    ${RED}✗ Failed${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}✨ Conversion complete!${NC}"
echo ""
echo "Summary:"
echo "  ✓ JPG files: converted with quality 85"
echo "  ✓ PNG files: converted with quality 90"
echo "  ✓ All original files are preserved"
echo ""
echo "Next steps:"
echo "  1. Verify the converted WebP files look good"
echo "  2. Delete the original JPG/PNG files if satisfied"
echo "  3. Push the changes to GitHub"
