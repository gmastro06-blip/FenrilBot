param(
  [string]$ActionTitle = "",
  [string]$CaptureTitle = "Proyector en ventana (Fuente) - Tibia_Fuente",
  [switch]$MouseTest,
  [switch]$ClickTest,
  [switch]$ClickAll,
  [switch]$ForceMssFallback
)

$ErrorActionPreference = 'Stop'

# Repo root = parent of scripts/
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

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
  $env:FENRIL_BLACK_FRAME_THRESHOLD = '0'
} else {
  Remove-Item Env:FENRIL_BLACK_FRAME_THRESHOLD -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_MSS_FALLBACK -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_MSS_FALLBACK_ON_NONE -ErrorAction SilentlyContinue
}

# Visual transform validation
if ($MouseTest) {
  $env:FENRIL_DUAL_MOUSE_TEST = '1'
  $env:FENRIL_ACTIVATE_ACTION_WINDOW = '1'
} else {
  $env:FENRIL_DUAL_MOUSE_TEST = '0'
}

if ($ClickTest) {
  $env:FENRIL_DUAL_CLICK_TEST = '1'
} else {
  $env:FENRIL_DUAL_CLICK_TEST = '0'
}

if ($ClickAll) {
  $env:FENRIL_DUAL_CLICK_ALL = '1'
} else {
  $env:FENRIL_DUAL_CLICK_ALL = '0'
}

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  throw "Python venv not found at $python. Create it first (poetry install or python -m venv .venv + pip install -r requirements.txt)."
}

Write-Host "Running dual debug with:" -ForegroundColor Cyan
Write-Host "  FENRIL_ACTION_WINDOW_TITLE=$($env:FENRIL_ACTION_WINDOW_TITLE)" -ForegroundColor Cyan
Write-Host "  FENRIL_CAPTURE_WINDOW_TITLE=$($env:FENRIL_CAPTURE_WINDOW_TITLE)" -ForegroundColor Cyan
Write-Host "  MouseTest=$($env:FENRIL_DUAL_MOUSE_TEST) ClickTest=$($env:FENRIL_DUAL_CLICK_TEST)" -ForegroundColor Cyan

if ($MouseTest -or $ClickTest) {
  Write-Host "Starting in 5 seconds (switch to Tibia now)..." -ForegroundColor Yellow
  Start-Sleep -Seconds 5
}

& $python scripts\debug_capture_dual.py
