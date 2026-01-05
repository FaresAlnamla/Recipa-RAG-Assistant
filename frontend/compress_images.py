#!/usr/bin/env python3
"""
Image Compression Script - Convert JPG/PNG to optimized WebP
Requires: pillow (PIL)
Install: pip install pillow
"""

import os
from pathlib import Path
from PIL import Image
import sys

def compress_images():
    """Convert and compress all JPG/PNG images to WebP format"""
    
    # Get public folder path
    script_dir = Path(__file__).parent
    public_dir = script_dir / "public"
    
    if not public_dir.exists():
        print(f"❌ Public folder not found at: {public_dir}")
        return False
    
    print("🖼️  Starting image compression to WebP format...\n")
    
    # Image compression settings
    quality_settings = {
        '.jpg': 85,
        '.jpeg': 85,
        '.png': 90
    }
    
    converted_count = 0
    total_saved = 0
    
    # Find all image files
    for ext in ['.jpg', '.jpeg', '.png']:
        image_files = list(public_dir.glob(f'*{ext}'))
        
        if not image_files:
            continue
            
        print(f"Converting {ext.upper()} files...")
        
        for img_path in image_files:
            try:
                quality = quality_settings[ext]
                output_path = img_path.with_suffix('.webp')
                
                # Get original size
                original_size = os.path.getsize(img_path) / 1024  # KB
                
                # Open and convert image
                img = Image.open(img_path)
                
                # Convert RGBA to RGB if necessary (WebP handles both)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Save as WebP with optimization
                img.save(
                    output_path,
                    'WEBP',
                    quality=quality,
                    method=6  # Slowest but best compression
                )
                
                # Get compressed size
                compressed_size = os.path.getsize(output_path) / 1024  # KB
                saved = original_size - compressed_size
                saved_percent = (saved / original_size) * 100
                total_saved += saved
                
                print(f"  ✓ {img_path.name} ({original_size:.1f}KB) → {output_path.name} ({compressed_size:.1f}KB)")
                print(f"    Saved: {saved:.1f}KB ({saved_percent:.1f}%)")
                
                converted_count += 1
                
            except Exception as e:
                print(f"  ✗ Failed to convert {img_path.name}: {str(e)}")
                return False
    
    print(f"\n✨ Conversion complete!")
    print(f"   Total files converted: {converted_count}")
    print(f"   Total space saved: {total_saved:.1f}KB ({(total_saved/1024):.1f}MB)")
    
    if converted_count > 0:
        print(f"\n✅ All images successfully compressed to WebP!")
        print(f"\nNext steps:")
        print(f"  1. Verify images display correctly on the website")
        print(f"  2. Delete original JPG/PNG files if satisfied (optional)")
        print(f"  3. Commit changes: git add -A && git commit -m 'Compress images to WebP'")
        return True
    else:
        print(f"\n⚠️  No images were converted")
        return False

if __name__ == "__main__":
    try:
        # Check if Pillow is installed
        import PIL
    except ImportError:
        print("❌ Pillow is not installed")
        print("\nInstall it with: pip install pillow")
        sys.exit(1)
    
    success = compress_images()
    sys.exit(0 if success else 1)
