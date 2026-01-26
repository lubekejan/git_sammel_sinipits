# ==========================
# SVG → PNG Batch-Konverter
# ==========================

$root = Get-Location
$inputDir = Join-Path $root "output"

# Optional: Zielordner (wenn leer = gleiche Ordnerstruktur)
$outputDir = $inputDir

# Inkscape Pfad (falls nicht im PATH, sonst einfach "inkscape")
$inkscape = "inkscape"
# Beispiel fest verdrahtet:
# $inkscape = "C:\Program Files\Inkscape\bin\inkscape.exe"

$dpi = 300

Write-Host "Konvertiere SVGs in: $inputDir"
Write-Host "--------------------------------"

Get-ChildItem $inputDir -Recurse -Filter *.svg | ForEach-Object {

    $svg = $_.FullName
    $relative = $svg.Substring($inputDir.Length)
    $png = Join-Path $outputDir ($relative -replace "\.svg$", ".png")

    # Zielordner sicherstellen
    $pngDir = Split-Path $png
    New-Item -ItemType Directory -Force -Path $pngDir | Out-Null

    Write-Host "→ $relative"

    & $inkscape $svg `
        --export-type=png `
        --export-filename=$png `
        --export-dpi=$dpi
}

Write-Host "Fertig."
