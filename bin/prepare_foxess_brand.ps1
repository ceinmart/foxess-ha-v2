# Versao: v0.1.4b3
# Data/hora de criacao: 2026-04-15 15:18:00
# Criado por: Codex / OpenAI
# Projeto/Pasta: C:\\tmp\\foxess-ha.v2

param(
    [string]$SourceUrl = "https://www.tritec-energy.com/wp-content/uploads/2022/03/fox-ess-logo-400x160.png"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$repoRoot = Split-Path -Parent $PSScriptRoot
$brandDir = Join-Path $repoRoot "custom_components\\foxess_ha_v2\\brand"
$sourceDir = Join-Path $brandDir "source"
$sourcePath = Join-Path $sourceDir "foxess-logo-400x160.png"

if (-not (Test-Path $sourceDir)) {
    New-Item -ItemType Directory -Path $sourceDir | Out-Null
}

python -c "from urllib.request import urlopen; from pathlib import Path; p=Path(r'$sourcePath'); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(urlopen('$SourceUrl', timeout=30).read()); print('Downloaded:', p)"

function Get-AlphaBounds([System.Drawing.Bitmap]$bmp, [int]$startX = 0) {
    $minX = $bmp.Width
    $minY = $bmp.Height
    $maxX = -1
    $maxY = -1

    for ($y = 0; $y -lt $bmp.Height; $y++) {
        for ($x = $startX; $x -lt $bmp.Width; $x++) {
            if ($bmp.GetPixel($x, $y).A -gt 10) {
                if ($x -lt $minX) { $minX = $x }
                if ($y -lt $minY) { $minY = $y }
                if ($x -gt $maxX) { $maxX = $x }
                if ($y -gt $maxY) { $maxY = $y }
            }
        }
    }

    if ($maxX -lt $minX -or $maxY -lt $minY) {
        return $null
    }

    return New-Object System.Drawing.Rectangle($minX, $minY, ($maxX - $minX + 1), ($maxY - $minY + 1))
}

function Get-AlphaComponents([System.Drawing.Bitmap]$bmp) {
    $visited = New-Object "bool[,]" $bmp.Width, $bmp.Height
    $components = @()

    for ($y = 0; $y -lt $bmp.Height; $y++) {
        for ($x = 0; $x -lt $bmp.Width; $x++) {
            if ($visited[$x, $y]) {
                continue
            }

            if ($bmp.GetPixel($x, $y).A -le 10) {
                $visited[$x, $y] = $true
                continue
            }

            $queue = New-Object "System.Collections.Generic.Queue[System.Drawing.Point]"
            $queue.Enqueue((New-Object System.Drawing.Point($x, $y)))
            $visited[$x, $y] = $true

            $minX = $x
            $maxX = $x
            $minY = $y
            $maxY = $y
            $pixelCount = 0
            $sumX = 0

            while ($queue.Count -gt 0) {
                $p = $queue.Dequeue()
                $px = $p.X
                $py = $p.Y

                $pixelCount++
                $sumX += $px

                if ($px -lt $minX) { $minX = $px }
                if ($px -gt $maxX) { $maxX = $px }
                if ($py -lt $minY) { $minY = $py }
                if ($py -gt $maxY) { $maxY = $py }

                if ($px -gt 0) {
                    $nx = $px - 1
                    $ny = $py
                    if (-not $visited[$nx, $ny]) {
                        $visited[$nx, $ny] = $true
                        if ($bmp.GetPixel($nx, $ny).A -gt 10) {
                            $queue.Enqueue((New-Object System.Drawing.Point($nx, $ny)))
                        }
                    }
                }

                if ($px -lt ($bmp.Width - 1)) {
                    $nx = $px + 1
                    $ny = $py
                    if (-not $visited[$nx, $ny]) {
                        $visited[$nx, $ny] = $true
                        if ($bmp.GetPixel($nx, $ny).A -gt 10) {
                            $queue.Enqueue((New-Object System.Drawing.Point($nx, $ny)))
                        }
                    }
                }

                if ($py -gt 0) {
                    $nx = $px
                    $ny = $py - 1
                    if (-not $visited[$nx, $ny]) {
                        $visited[$nx, $ny] = $true
                        if ($bmp.GetPixel($nx, $ny).A -gt 10) {
                            $queue.Enqueue((New-Object System.Drawing.Point($nx, $ny)))
                        }
                    }
                }

                if ($py -lt ($bmp.Height - 1)) {
                    $nx = $px
                    $ny = $py + 1
                    if (-not $visited[$nx, $ny]) {
                        $visited[$nx, $ny] = $true
                        if ($bmp.GetPixel($nx, $ny).A -gt 10) {
                            $queue.Enqueue((New-Object System.Drawing.Point($nx, $ny)))
                        }
                    }
                }
            }

            $components += [PSCustomObject]@{
                Rect       = New-Object System.Drawing.Rectangle($minX, $minY, ($maxX - $minX + 1), ($maxY - $minY + 1))
                PixelCount = $pixelCount
                CenterX    = ([double]$sumX / [double]$pixelCount)
            }
        }
    }

    return $components
}

function Crop-Bitmap([System.Drawing.Bitmap]$bmp, [System.Drawing.Rectangle]$rect) {
    $out = New-Object System.Drawing.Bitmap -ArgumentList @(
        $rect.Width,
        $rect.Height,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $g = [System.Drawing.Graphics]::FromImage($out)
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($bmp, (New-Object System.Drawing.Rectangle 0, 0, $rect.Width, $rect.Height), $rect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    return $out
}

function Resize-Bitmap([System.Drawing.Bitmap]$bmp, [int]$width, [int]$height) {
    $out = New-Object System.Drawing.Bitmap -ArgumentList @(
        $width,
        $height,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $g = [System.Drawing.Graphics]::FromImage($out)
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($bmp, 0, 0, $width, $height)
    $g.Dispose()
    return $out
}

function Save-Png([System.Drawing.Bitmap]$bmp, [string]$path) {
    $ms = New-Object System.IO.MemoryStream
    try {
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        [System.IO.File]::WriteAllBytes($path, $ms.ToArray())
    } finally {
        $ms.Dispose()
    }
}

$src = [System.Drawing.Bitmap]::FromFile($sourcePath)
try {
    $allBounds = Get-AlphaBounds $src 0
    if ($null -eq $allBounds) {
        throw "No non-transparent pixels found in source logo."
    }

    $logoCrop = Crop-Bitmap $src $allBounds
    try {
        $logoPath = Join-Path $brandDir "logo.png"
        $logo2xPath = Join-Path $brandDir "logo@2x.png"
        Save-Png $logoCrop $logoPath

        $logo2x = Resize-Bitmap $logoCrop ($logoCrop.Width * 2) ($logoCrop.Height * 2)
        try {
            Save-Png $logo2x $logo2xPath
        } finally {
            $logo2x.Dispose()
        }
    } finally {
        $logoCrop.Dispose()
    }

    $components = Get-AlphaComponents $src
    $iconComponent = $components |
        Where-Object { $_.CenterX -ge ($src.Width * 0.45) } |
        Sort-Object PixelCount -Descending |
        Select-Object -First 1

    if ($null -eq $iconComponent) {
        $iconComponent = $components | Sort-Object PixelCount -Descending | Select-Object -First 1
    }

    $iconBounds = $null
    if ($null -ne $iconComponent) {
        $iconBounds = $iconComponent.Rect
    }
    if ($null -eq $iconBounds) {
        $iconBounds = $allBounds
    }

    $pad = [int][Math]::Ceiling([Math]::Max($iconBounds.Width, $iconBounds.Height) * 0.08)
    $x = [Math]::Max(0, $iconBounds.X - $pad)
    $y = [Math]::Max(0, $iconBounds.Y - $pad)
    $r = [Math]::Min($src.Width - 1, $iconBounds.X + $iconBounds.Width - 1 + $pad)
    $b = [Math]::Min($src.Height - 1, $iconBounds.Y + $iconBounds.Height - 1 + $pad)
    $iconRect = New-Object System.Drawing.Rectangle($x, $y, ($r - $x + 1), ($b - $y + 1))

    $iconCrop = Crop-Bitmap $src $iconRect
    try {
        $side = [Math]::Max($iconCrop.Width, $iconCrop.Height)
        $canvas = New-Object System.Drawing.Bitmap -ArgumentList @(
            $side,
            $side,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        try {
            $g = [System.Drawing.Graphics]::FromImage($canvas)
            $g.Clear([System.Drawing.Color]::Transparent)
            $dx = [int](($side - $iconCrop.Width) / 2)
            $dy = [int](($side - $iconCrop.Height) / 2)
            $g.DrawImage($iconCrop, $dx, $dy, $iconCrop.Width, $iconCrop.Height)
            $g.Dispose()

            $iconPath = Join-Path $brandDir "icon.png"
            $icon2xPath = Join-Path $brandDir "icon@2x.png"

            $icon256 = Resize-Bitmap $canvas 256 256
            try {
                Save-Png $icon256 $iconPath
            } finally {
                $icon256.Dispose()
            }

            $icon512 = Resize-Bitmap $canvas 512 512
            try {
                Save-Png $icon512 $icon2xPath
            } finally {
                $icon512.Dispose()
            }
        } finally {
            $canvas.Dispose()
        }
    } finally {
        $iconCrop.Dispose()
    }
} finally {
    $src.Dispose()
}

foreach ($name in @("icon.png", "icon@2x.png", "logo.png", "logo@2x.png")) {
    $path = Join-Path $brandDir $name
    $img = [System.Drawing.Image]::FromFile($path)
    try {
        Write-Output ("{0} {1}x{2}" -f $name, $img.Width, $img.Height)
    } finally {
        $img.Dispose()
    }
}
