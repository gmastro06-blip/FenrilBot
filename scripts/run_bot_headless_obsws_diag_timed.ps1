# Headless + OBS WebSocket + extra diagnostics for battle list / targeting.
# Timed variant: exits automatically after N seconds.

param(
  [int]$Seconds = 180,
  [int]$FreezeWaypoints = 1,
  [int]$AttackOnly = 1,
  [ValidateSet('premium','free')][string]$AccountType = 'premium',
  [int]$ForceLootTest = 0,
  [int]$DumpLootDebug = 0
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

# Loot behavior
$env:FENRIL_ACCOUNT_TYPE = $AccountType
# Optional overrides:
#   $env:FENRIL_LOOT_METHOD = 'open_drag'   # force free-style open + drag
#   $env:FENRIL_LOOT_METHOD = 'quick'       # force quick-loot style
#   $env:FENRIL_LOOT_CLICK  = 'left'        # modern controls
#   $env:FENRIL_LOOT_CLICK  = 'right'       # classic controls

# For supervised kill+loot validation, keep the character stationary and focused.
if ($AttackOnly -ne 0) {
  $env:FENRIL_ATTACK_ONLY = '1'
} else {
  Remove-Item Env:FENRIL_ATTACK_ONLY -ErrorAction SilentlyContinue
}

# Diagnostic: periodically force looting around player (no kill required)
if ($ForceLootTest -ne 0) {
  $env:FENRIL_DEBUG_FORCE_LOOT = '1'
} elseif (-not $env:FENRIL_DEBUG_FORCE_LOOT) {
  Remove-Item Env:FENRIL_DEBUG_FORCE_LOOT -ErrorAction SilentlyContinue
}

# Diagnostic: dump screenshot+meta when open+drag can't find containers/items
if ($DumpLootDebug -ne 0) {
  $env:FENRIL_DUMP_LOOT_DEBUG = '1'
} elseif (-not $env:FENRIL_DUMP_LOOT_DEBUG) {
  Remove-Item Env:FENRIL_DUMP_LOOT_DEBUG -ErrorAction SilentlyContinue
}

# For supervised loot validation, keep the character stationary by default.
if ($FreezeWaypoints -ne 0) {
  $env:FENRIL_FREEZE_WAYPOINTS = '1'
} else {
  Remove-Item Env:FENRIL_FREEZE_WAYPOINTS -ErrorAction SilentlyContinue
}

# Allow input (ESC stops).
Remove-Item Env:FENRIL_DISABLE_INPUT -ErrorAction SilentlyContinue

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'
& $python (Join-Path $PSScriptRoot 'run_bot_headless.py') --seconds $Seconds
