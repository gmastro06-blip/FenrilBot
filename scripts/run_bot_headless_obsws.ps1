# Run FenrilBot headless (no UI) using OBS WebSocket capture.
# Press ESC anytime to stop.

$ErrorActionPreference = 'Stop'

$env:FENRIL_CAPTURE_BACKEND = 'obsws'
$env:FENRIL_OBS_SOURCE = 'Tibia_Fuente'
$env:FENRIL_OBS_HOST = '127.0.0.1'
$env:FENRIL_OBS_PORT = '4455'

# Default: start running immediately.
$env:FENRIL_START_PAUSED = '0'

# IMPORTANT: allow input (clicks/keys) in normal runs.
Remove-Item Env:FENRIL_DISABLE_INPUT -ErrorAction SilentlyContinue

# Optional diagnostics:
# $env:FENRIL_LOG_LOOT_EVENTS = '1'

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'
& $python (Join-Path $PSScriptRoot 'run_bot_headless.py')
