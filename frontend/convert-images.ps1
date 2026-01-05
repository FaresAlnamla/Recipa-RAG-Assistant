# Image Conversion Script - JPG/PNG to WebP (PowerShell for Windows)
# This script converts all images in the public folder to WebP format
# Requires: cwebp installed (download from https://developers.google.com/speed/webp/download)

Write-Host "🖼️  Starting image conversion to WebP format..." -ForegroundColor Cyan
Write-Host ""

# Check if cwebp is installed
$cwebpPath = (Get-Command cwebp -ErrorAction SilentlyContinue).Source
if (-not $cwebpPath) {
    Write-Host "❌ cwebp is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Download WebP tools from:"
    Write-Host "  https://developers.google.com/speed/webp/download"
    Write-Host ""
    Write-Host "Or install via Chocolatey:"
    Write-Host "  choco install webp"
    exit 1
}

Write-Host "✅ cwebp found at: $cwebpPath" -ForegroundColor Green
Write-Host ""

# Navigate to public folder
$publicPath = Join-Path (Split-Path -Parent $PSCommandPath) "public"
if (-not (Test-Path $publicPath)) {
    Write-Host "❌ Public folder not found at: $publicPath" -ForegroundColor Red
    exit 1
}

Push-Location $publicPath

# Convert JPG files
Write-Host "Converting JPG files..." -ForegroundColor Yellow
$jpgFiles = Get-ChildItem -Filter "*.jpg" -File

if ($jpgFiles) {
    foreach ($file in $jpgFiles) {
        $outputName = $file.BaseName + ".webp"
        Write-Host "  Converting: $($file.Name) → $outputName"
        
        & cwebp -q 85 -m 6 $file.FullName -o $outputName
        
        if ($LASTEXITCODE -eq 0) {
            $originalSize = (Get-Item $file.FullName).Length / 1KB
            $newSize = (Get-Item $outputName).Length / 1KB
            $saved = [math]::Round(($originalSize - $newSize) / $originalSize * 100, 1)
            Write-Host "    ✓ Done (Saved: ${saved}%)" -ForegroundColor Green
        } else {
            Write-Host "    ✗ Failed" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  No JPG files found" -ForegroundColor Gray
}

Write-Host ""

# Convert PNG files
Write-Host "Converting PNG files..." -ForegroundColor Yellow
$pngFiles = Get-ChildItem -Filter "*.png" -File

if ($pngFiles) {
    foreach ($file in $pngFiles) {
        $outputName = $file.BaseName + ".webp"
        Write-Host "  Converting: $($file.Name) → $outputName"
        
        & cwebp -q 90 -m 6 $file.FullName -o $outputName
        
        if ($LASTEXITCODE -eq 0) {
            $originalSize = (Get-Item $file.FullName).Length / 1KB
            $newSize = (Get-Item $outputName).Length / 1KB
            $saved = [math]::Round(($originalSize - $newSize) / $originalSize * 100, 1)
            Write-Host "    ✓ Done (Saved: ${saved}%)" -ForegroundColor Green
        } else {
            Write-Host "    ✗ Failed" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  No PNG files found" -ForegroundColor Gray
}

Pop-Location

Write-Host ""
Write-Host "✨ Conversion complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:"
Write-Host "  ✓ JPG files: converted with quality 85 (balanced compression)"
Write-Host "  ✓ PNG files: converted with quality 90 (high quality)"
Write-Host "  ✓ All original files are preserved"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Check the public folder for .webp files"
Write-Host "  2. Verify quality: compare original and WebP versions"
Write-Host "  3. Delete original JPG/PNG files if satisfied"
Write-Host "  4. Run: git add . && git commit -m 'Optimize images to WebP format'"
Write-Host ""
