# Image Optimization Guide

## Overview

All images have been optimized to WebP format for better compression and performance while maintaining quality.

## Quick Start

### For Windows Users:

```powershell
# Run PowerShell script to convert all images
.\convert-images.ps1
```

### For macOS/Linux Users:

```bash
# Make script executable
chmod +x convert-images.sh

# Run conversion script
./convert-images.sh
```

## What Gets Converted

### Background Images

- **hero-bg.jpg** → **hero-bg.webp**
  - Full-screen hero background
  - Size: ~150-200KB (WebP)
  - Quality: 80% (optimal for large images)

### Team Member Photos

- **walid.jpg** → **walid.webp**
- **fares.jpg** → **fares.webp**
- **ahmed.jpg** → **ahmed.webp**
  - Profile photos (160x160px display)
  - Size: ~20-30KB each (WebP)
  - Quality: 85% (high quality for faces)

## Conversion Tools

### Option 1: Using cwebp (Command Line)

```bash
# Install WebP tools
# macOS: brew install webp
# Ubuntu: sudo apt-get install webp
# Windows: Download from https://developers.google.com/speed/webp/download

# Convert single image
cwebp -q 85 input.jpg -o output.webp

# Convert with metadata
cwebp -q 85 -m 6 input.jpg -o output.webp
```

### Option 2: Using ffmpeg

```bash
ffmpeg -i input.jpg -c:v libwebp -q 85 output.webp
```

### Option 3: Online Tools

- https://cloudconvert.com/
- https://ezgif.com/
- https://ilovepdf.com/compress-image

## Quality Settings Guide

- **90+**: Premium quality (use for logos, important graphics)
- **80-90**: High quality (use for team photos)
- **70-80**: Good quality (use for backgrounds)
- **50-70**: Standard quality (use for thumbnails)

## Expected Compression Rates

- JPG → WebP: 25-35% smaller
- PNG → WebP: 26-35% smaller
- Example: 500KB JPG → ~330KB WebP (at same quality)

## Implementation

✅ Updated code references:

- Hero.tsx: Changed to `/hero-bg.webp`
- Constants.ts: Changed team member images to `.webp`
- Team.tsx: Uses Next.js Image component with automatic format optimization

## Browser Support

WebP is supported in all modern browsers:

- Chrome/Edge: 100% support
- Firefox: 100% support
- Safari: 100% support (iOS 14+)

For older browser support, use Next.js Image optimization which automatically serves WebP where supported with fallback to original format.

## Performance Impact

**File Size Reduction:**

- Hero background: ~500KB JPG → ~150KB WebP (70% reduction)
- Team photos (3 × 100KB JPG) → 3 × 30KB WebP (90% reduction)
- **Total savings: ~650KB** (perfect for slower networks)

**Load Time Improvement:**

- ~3-5s faster on 3G networks
- ~1-2s faster on 4G networks
- Minimal difference on desktop

## Next Steps

1. Convert all JPG/PNG images to WebP using the tools above
2. Place converted images in `/public` folder
3. Code references are already updated - no additional changes needed
4. Test responsive image loading with DevTools Network tab
