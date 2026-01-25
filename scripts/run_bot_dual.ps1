param(
  [string]$ActionTitle = "",
  [string]$CaptureTitle = "",
  [switch]$ForceMssFallback,
  [switch]$Preflight,
  [switch]$PreflightOnly,
  [switch]$VerboseDiag,
  [switch]$TargetingDiag,
  [switch]$DumpBattlelistOnEmpty,
  [double]$BattlelistGraceS = 0.0
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

if ($CaptureTitle -and $CaptureTitle.Trim().Length -gt 0) {
  $env:FENRIL_CAPTURE_WINDOW_TITLE = $CaptureTitle
} else {
  Remove-Item Env:FENRIL_CAPTURE_WINDOW_TITLE -ErrorAction SilentlyContinue
}

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

# Diagnostics (opt-in)
if ($VerboseDiag) {
  $env:FENRIL_WARN_ON_WINDOW_MISS = '1'
  $env:FENRIL_WINDOW_DIAG = '1'
  $env:FENRIL_INPUT_DIAG = '1'
  $env:FENRIL_CONSOLE_LOG = '1'
  $env:FENRIL_LOG_LEVEL = 'debug'
} else {
  Remove-Item Env:FENRIL_WINDOW_DIAG -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_INPUT_DIAG -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_CONSOLE_LOG -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_LOG_LEVEL -ErrorAction SilentlyContinue
  # Keep WARN_ON_WINDOW_MISS enabled; it's low-noise and very helpful in dual-window setups.
  $env:FENRIL_WARN_ON_WINDOW_MISS = '1'
}

# Targeting/battlelist diagnostics (opt-in)
if ($TargetingDiag) {
  $env:FENRIL_TARGETING_DIAG = '1'
  # Keep this warning on during diag runs; it helps catch incorrect Tibia filters.
  $env:FENRIL_WARN_ON_BATTLELIST_EMPTY = '1'
} else {
  Remove-Item Env:FENRIL_TARGETING_DIAG -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_WARN_ON_BATTLELIST_EMPTY -ErrorAction SilentlyContinue
}

if ($DumpBattlelistOnEmpty) {
  $env:FENRIL_DUMP_BATTLELIST_ON_EMPTY = '1'
  # Make dumps reasonably frequent during troubleshooting.
  $env:FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S = '30'
} else {
  Remove-Item Env:FENRIL_DUMP_BATTLELIST_ON_EMPTY -ErrorAction SilentlyContinue
  Remove-Item Env:FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S -ErrorAction SilentlyContinue
}

# Smooth brief battle list parsing glitches by reusing the last non-empty list
# for a short grace window (seconds). 0 disables.
if ($BattlelistGraceS -gt 0) {
  $env:FENRIL_BATTLELIST_GRACE_S = [string]$BattlelistGraceS
} else {
  Remove-Item Env:FENRIL_BATTLELIST_GRACE_S -ErrorAction SilentlyContinue
}

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
Write-Host "  VerboseDiag=$VerboseDiag" -ForegroundColor Cyan
Write-Host "  TargetingDiag=$TargetingDiag" -ForegroundColor Cyan
Write-Host "  DumpBattlelistOnEmpty=$DumpBattlelistOnEmpty" -ForegroundColor Cyan
Write-Host "  BattlelistGraceS=$BattlelistGraceS" -ForegroundColor Cyan
Write-Host "  FENRIL_WARN_ON_WINDOW_MISS=$($env:FENRIL_WARN_ON_WINDOW_MISS)" -ForegroundColor Cyan
Write-Host "  FENRIL_WINDOW_DIAG=$($env:FENRIL_WINDOW_DIAG)" -ForegroundColor Cyan
Write-Host "  FENRIL_INPUT_DIAG=$($env:FENRIL_INPUT_DIAG)" -ForegroundColor Cyan
Write-Host "  FENRIL_TARGETING_DIAG=$($env:FENRIL_TARGETING_DIAG)" -ForegroundColor Cyan
Write-Host "  FENRIL_WARN_ON_BATTLELIST_EMPTY=$($env:FENRIL_WARN_ON_BATTLELIST_EMPTY)" -ForegroundColor Cyan
Write-Host "  FENRIL_DUMP_BATTLELIST_ON_EMPTY=$($env:FENRIL_DUMP_BATTLELIST_ON_EMPTY)" -ForegroundColor Cyan
Write-Host "  FENRIL_BATTLELIST_GRACE_S=$($env:FENRIL_BATTLELIST_GRACE_S)" -ForegroundColor Cyan

if ($Preflight) {
  Write-Host "Preflight: resolving windows from profile/env..." -ForegroundColor Cyan
  & $python scripts\preflight_dual_windows.py
  if ($LASTEXITCODE -ne 0) {
    throw "Preflight failed (exit code $LASTEXITCODE)."
  }
}

if ($PreflightOnly) {
  Write-Host "PreflightOnly requested; not launching main.py" -ForegroundColor Cyan
  exit 0
}

& $python main.py
