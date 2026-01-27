# Run FenrilBot using OBS WebSocket capture (bypasses black-screen desktop capture).
# Adjust FENRIL_OBS_SOURCE to match your OBS source name.

$ErrorActionPreference = 'Stop'

$env:FENRIL_CAPTURE_BACKEND = 'obsws'
$env:FENRIL_OBS_SOURCE = 'Tibia_Fuente'
$env:FENRIL_OBS_HOST = '127.0.0.1'
$env:FENRIL_OBS_PORT = '4455'

# Default: start running immediately.
# If you want a safer start, change this to '1'.
$env:FENRIL_START_PAUSED = '0'

# IMPORTANT: allow input (clicks/keys) in normal runs.
Remove-Item Env:FENRIL_DISABLE_INPUT -ErrorAction SilentlyContinue

# Optional diagnostics:
# $env:FENRIL_WINDOW_DIAG = '1'
# $env:FENRIL_STATUS_LOG_INTERVAL = '2'
# $env:FENRIL_LOG_LOOT_EVENTS = '1'

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'
& $python (Join-Path $PSScriptRoot '..\main.py')
