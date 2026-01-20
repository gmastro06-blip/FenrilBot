param(
  [string]$ActionTitle = "",
  [string]$CaptureTitle = "Proyector en ventana (Fuente) - Tibia_Fuente",
  [switch]$ForceMssFallback
)

$ErrorActionPreference = 'Stop'

# Repo root = parent of scripts/
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

# Clear legacy single-window debug env vars to avoid confusion.
Remove-Item Env:FENRIL_WINDOW_TITLE -ErrorAction SilentlyContinue
Remove-Item Env:FENRIL_ACTIVATE_WINDOW -ErrorAction SilentlyContinue

# Window selection
if ($ActionTitle -and $ActionTitle.Trim().Length -gt 0) {
  $env:FENRIL_ACTION_WINDOW_TITLE = $ActionTitle
} else {
  Remove-Item Env:FENRIL_ACTION_WINDOW_TITLE -ErrorAction SilentlyContinue
}

$env:FENRIL_CAPTURE_WINDOW_TITLE = $CaptureTitle

# Capture robustness
if ($ForceMssFallback) {
  $env:FENRIL_MSS_FALLBACK = '1'
  $env:FENRIL_BLACK_FRAME_THRESHOLD = '2'
  # Make "dim/near-black" glitches count as black so fallback kicks in.
  $env:FENRIL_BLACK_MEAN_THRESHOLD = '25'
} else {
  Remove-Item Env:FENRIL_BLACK_FRAME_THRESHOLD -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_BLACK_MEAN_THRESHOLD -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_MSS_FALLBACK -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_MSS_FALLBACK_ON_NONE -ErrorAction SilentlyContinue
}

# Helpful: warn loudly instead of silently falling back.
$env:FENRIL_WARN_ON_WINDOW_MISS = '1'

# Better stability on transient dxcam glitches (hard-black frames).
$env:FENRIL_DXCAM_RETRY_ON_HARD_BLACK = '1'

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  throw "Python venv not found at $python. Create it first (poetry install or python -m venv .venv + pip install -r requirements.txt)."
}

Write-Host "Running bot with:" -ForegroundColor Cyan
Write-Host "  FENRIL_ACTION_WINDOW_TITLE=$($env:FENRIL_ACTION_WINDOW_TITLE)" -ForegroundColor Cyan
Write-Host "  FENRIL_CAPTURE_WINDOW_TITLE=$($env:FENRIL_CAPTURE_WINDOW_TITLE)" -ForegroundColor Cyan
Write-Host "  ForceMssFallback=$ForceMssFallback" -ForegroundColor Cyan

& $python main.py
