# Headless + OBS WebSocket + extra diagnostics for battle list / targeting.
# Timed variant: exits automatically after N seconds.

param(
  [int]$Seconds = 180
)

$ErrorActionPreference = 'Stop'

$env:FENRIL_CAPTURE_BACKEND = 'obsws'
$env:FENRIL_OBS_SOURCE = 'Tibia_Fuente'
$env:FENRIL_OBS_HOST = '127.0.0.1'
$env:FENRIL_OBS_PORT = '4455'

# Start running immediately.
$env:FENRIL_START_PAUSED = '0'

# Diagnostics
$env:FENRIL_STATUS_LOG_INTERVAL = '1'
$env:FENRIL_ATTACK_FROM_BATTLELIST = '1'
$env:FENRIL_TARGETING_DIAG = '1'
$env:FENRIL_DUMP_BATTLELIST_ON_EMPTY = '1'
$env:FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S = '15'
$env:FENRIL_LOG_LOOT_EVENTS = '1'

# Allow input (ESC stops).
Remove-Item Env:FENRIL_DISABLE_INPUT -ErrorAction SilentlyContinue

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'
& $python (Join-Path $PSScriptRoot 'run_bot_headless.py') --seconds $Seconds
