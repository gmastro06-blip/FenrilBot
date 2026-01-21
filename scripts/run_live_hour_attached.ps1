param(
  [int]$Seconds = 3600,
  [int]$StatusEverySeconds = 60,
  [string]$Tag = "attack_site",
  [switch]$ManualAutoAttack,
  [ValidateSet('hotkey','click')][string]$ManualAutoAttackMethod = 'hotkey',
  [string]$ManualAutoAttackHotkey = 'pageup',
  [double]$ManualAutoAttackIntervalS = 0.70,
  [switch]$FocusBeforeManualHotkey,
  [ValidateRange(1,3)][int]$ManualAutoAttackKeyRepeat = 1,
  [double]$ManualAutoAttackPreDelayS = 0.02
)

$ErrorActionPreference = 'Stop'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$tagPart = ("_{0}" -f $Tag).Replace(' ', '_')

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$debugDir = Join-Path $repoRoot 'debug'
New-Item -ItemType Directory -Force -Path $debugDir | Out-Null

$out = Join-Path $debugDir "live_hour_attached${tagPart}_${ts}.out.log"
$err = Join-Path $debugDir "live_hour_attached${tagPart}_${ts}.err.log"
$meta = Join-Path $debugDir "live_hour_attached${tagPart}_${ts}.meta.json"
$pidPath = Join-Path $debugDir "live_hour_attached${tagPart}_${ts}.pid.txt"

$python = (Resolve-Path (Join-Path $repoRoot '.venv\Scripts\python.exe')).Path

function Set-EnvDefault {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Value
  )
  $existing = [Environment]::GetEnvironmentVariable($Name, 'Process')
  if ([string]::IsNullOrEmpty($existing)) {
    [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
  }
}

# Env vars validated in previous debugging
$env:FENRIL_START_PAUSED = '0'
$env:FENRIL_ALLOW_ATTACK_WITHOUT_COORD = '1'
$env:FENRIL_ATTACK_FROM_BATTLELIST = '1'
$env:FENRIL_DISABLE_ARDUINO_CLICKS = '1'
$env:FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER = 'ctrl'
$env:FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON = 'left'
$env:FENRIL_ATTACK_CLICK_BUTTON = 'left'
$env:FENRIL_BLOCK_RIGHT_CLICK_ATTACK = '1'

# Optional: manual auto-attack mode
if ($ManualAutoAttack) {
  $env:FENRIL_MANUAL_AUTO_ATTACK = '1'
  $env:FENRIL_MANUAL_AUTO_ATTACK_METHOD = $ManualAutoAttackMethod
  $env:FENRIL_MANUAL_AUTO_ATTACK_HOTKEY = $ManualAutoAttackHotkey
  $env:FENRIL_MANUAL_AUTO_ATTACK_INTERVAL_S = [string]$ManualAutoAttackIntervalS

  # Manual hotkey reliability knobs
  $env:FENRIL_MANUAL_AUTO_ATTACK_KEY_REPEAT = [string]$ManualAutoAttackKeyRepeat
  $env:FENRIL_MANUAL_AUTO_ATTACK_PRE_DELAY_S = [string]$ManualAutoAttackPreDelayS
  if ($FocusBeforeManualHotkey) {
    $env:FENRIL_FOCUS_ACTION_WINDOW_BEFORE_MANUAL_HOTKEY = '1'
  }
}
$env:FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK = '1'
$env:FENRIL_FOCUS_AFTER_S = '0.05'

# Production defaults: keep the run clean (no debug folder spam).
# You can still override by exporting env vars before running this script.
Set-EnvDefault -Name 'FENRIL_INPUT_DIAG' -Value '0'
Set-EnvDefault -Name 'FENRIL_TARGETING_DIAG' -Value '0'
Set-EnvDefault -Name 'FENRIL_WINDOW_DIAG' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_TASK_ON_TIMEOUT' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_BLACK_CAPTURE' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_BLACK_CAPTURE_MIN_INTERVAL_S' -Value '60'
Set-EnvDefault -Name 'FENRIL_DUMP_RADAR_ON_FAIL' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_RADAR_MIN_INTERVAL_S' -Value '60'
Set-EnvDefault -Name 'FENRIL_DUMP_RADAR_PERSISTENT' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_RADAR_PERSISTENT_MIN_INTERVAL_S' -Value '120'
Set-EnvDefault -Name 'FENRIL_DUMP_BATTLELIST_ON_EMPTY' -Value '0'
Set-EnvDefault -Name 'FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S' -Value '120'

# Make radar tools locator more tolerant to projector scaling.
$env:FENRIL_RADAR_TOOLS_CONFIDENCE = '0.75'
$env:FENRIL_RADAR_TOOLS_MIN_SCALE = '0.70'
$env:FENRIL_RADAR_TOOLS_MAX_SCALE = '1.35'
$env:FENRIL_RADAR_TOOLS_SCALE_STEPS = '14'

# Make battle list locators more tolerant to scaling.
$env:FENRIL_BATTLELIST_ICON_CONFIDENCE = '0.80'
$env:FENRIL_BATTLELIST_ICON_MIN_SCALE = '0.70'
$env:FENRIL_BATTLELIST_ICON_MAX_SCALE = '1.35'
$env:FENRIL_BATTLELIST_ICON_SCALE_STEPS = '14'
$env:FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE = '0.80'
$env:FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE = '0.70'
$env:FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE = '1.35'
$env:FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS = '14'

# Supervised run: stay put and just attack (avoid depot/waypoints).
$env:FENRIL_ATTACK_ONLY = '1'
$env:FENRIL_CAVEBOT_ENABLED = '0'
$env:FENRIL_RUN_TO_CREATURES = '0'

@{
  ts = $ts
  tag = $Tag
  seconds = $Seconds
  out = $out
  err = $err
  pidPath = $pidPath
  env = @{
    FENRIL_START_PAUSED = $env:FENRIL_START_PAUSED
    FENRIL_ALLOW_ATTACK_WITHOUT_COORD = $env:FENRIL_ALLOW_ATTACK_WITHOUT_COORD
    FENRIL_ATTACK_FROM_BATTLELIST = $env:FENRIL_ATTACK_FROM_BATTLELIST
    FENRIL_DISABLE_ARDUINO_CLICKS = $env:FENRIL_DISABLE_ARDUINO_CLICKS
    FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER = $env:FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER
    FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON = $env:FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON
    FENRIL_ATTACK_CLICK_BUTTON = $env:FENRIL_ATTACK_CLICK_BUTTON
    FENRIL_BLOCK_RIGHT_CLICK_ATTACK = $env:FENRIL_BLOCK_RIGHT_CLICK_ATTACK
    FENRIL_MANUAL_AUTO_ATTACK = $env:FENRIL_MANUAL_AUTO_ATTACK
    FENRIL_MANUAL_AUTO_ATTACK_METHOD = $env:FENRIL_MANUAL_AUTO_ATTACK_METHOD
    FENRIL_MANUAL_AUTO_ATTACK_HOTKEY = $env:FENRIL_MANUAL_AUTO_ATTACK_HOTKEY
    FENRIL_MANUAL_AUTO_ATTACK_INTERVAL_S = $env:FENRIL_MANUAL_AUTO_ATTACK_INTERVAL_S
    FENRIL_MANUAL_AUTO_ATTACK_KEY_REPEAT = $env:FENRIL_MANUAL_AUTO_ATTACK_KEY_REPEAT
    FENRIL_MANUAL_AUTO_ATTACK_PRE_DELAY_S = $env:FENRIL_MANUAL_AUTO_ATTACK_PRE_DELAY_S
    FENRIL_FOCUS_ACTION_WINDOW_BEFORE_MANUAL_HOTKEY = $env:FENRIL_FOCUS_ACTION_WINDOW_BEFORE_MANUAL_HOTKEY
    FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK = $env:FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK
    FENRIL_FOCUS_AFTER_S = $env:FENRIL_FOCUS_AFTER_S
    FENRIL_INPUT_DIAG = $env:FENRIL_INPUT_DIAG
    FENRIL_TARGETING_DIAG = $env:FENRIL_TARGETING_DIAG
    FENRIL_WINDOW_DIAG = $env:FENRIL_WINDOW_DIAG
    FENRIL_DUMP_TASK_ON_TIMEOUT = $env:FENRIL_DUMP_TASK_ON_TIMEOUT
    FENRIL_DUMP_BLACK_CAPTURE = $env:FENRIL_DUMP_BLACK_CAPTURE
    FENRIL_DUMP_BLACK_CAPTURE_MIN_INTERVAL_S = $env:FENRIL_DUMP_BLACK_CAPTURE_MIN_INTERVAL_S
    FENRIL_DUMP_RADAR_ON_FAIL = $env:FENRIL_DUMP_RADAR_ON_FAIL
    FENRIL_DUMP_RADAR_MIN_INTERVAL_S = $env:FENRIL_DUMP_RADAR_MIN_INTERVAL_S
    FENRIL_DUMP_RADAR_PERSISTENT = $env:FENRIL_DUMP_RADAR_PERSISTENT
    FENRIL_DUMP_RADAR_PERSISTENT_MIN_INTERVAL_S = $env:FENRIL_DUMP_RADAR_PERSISTENT_MIN_INTERVAL_S
    FENRIL_DUMP_BATTLELIST_ON_EMPTY = $env:FENRIL_DUMP_BATTLELIST_ON_EMPTY
    FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S = $env:FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S
    FENRIL_RADAR_TOOLS_CONFIDENCE = $env:FENRIL_RADAR_TOOLS_CONFIDENCE
    FENRIL_RADAR_TOOLS_MIN_SCALE = $env:FENRIL_RADAR_TOOLS_MIN_SCALE
    FENRIL_RADAR_TOOLS_MAX_SCALE = $env:FENRIL_RADAR_TOOLS_MAX_SCALE
    FENRIL_RADAR_TOOLS_SCALE_STEPS = $env:FENRIL_RADAR_TOOLS_SCALE_STEPS
    FENRIL_BATTLELIST_ICON_CONFIDENCE = $env:FENRIL_BATTLELIST_ICON_CONFIDENCE
    FENRIL_BATTLELIST_ICON_MIN_SCALE = $env:FENRIL_BATTLELIST_ICON_MIN_SCALE
    FENRIL_BATTLELIST_ICON_MAX_SCALE = $env:FENRIL_BATTLELIST_ICON_MAX_SCALE
    FENRIL_BATTLELIST_ICON_SCALE_STEPS = $env:FENRIL_BATTLELIST_ICON_SCALE_STEPS
    FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE = $env:FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE
    FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE = $env:FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE
    FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE = $env:FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE
    FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS = $env:FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS
    FENRIL_ATTACK_ONLY = $env:FENRIL_ATTACK_ONLY
    FENRIL_CAVEBOT_ENABLED = $env:FENRIL_CAVEBOT_ENABLED
    FENRIL_RUN_TO_CREATURES = $env:FENRIL_RUN_TO_CREATURES
  }
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $meta

"START attached run: $ts tag=$Tag seconds=$Seconds" | Write-Host
"OUT: $out" | Write-Host
"ERR: $err" | Write-Host

$p = Start-Process -FilePath $python -ArgumentList @('-u','main.py') -WorkingDirectory $repoRoot -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Set-Content -Encoding ASCII -LiteralPath $pidPath -Value $p.Id

$deadline = (Get-Date).AddSeconds($Seconds)
$nextStatus = Get-Date

while ((Get-Date) -lt $deadline) {
  if ((Get-Date) -ge $nextStatus) {
    $outLen = 0
    $errLen = 0
    if (Test-Path -LiteralPath $out) { $outLen = (Get-Item -LiteralPath $out).Length }
    if (Test-Path -LiteralPath $err) { $errLen = (Get-Item -LiteralPath $err).Length }

    $lastTarget = $null
    try {
      $lastTarget = Select-String -Path $out -Pattern "\[fenril\]\[info\] targeting:" | Select-Object -Last 1 | ForEach-Object { $_.Line }
    } catch {}

    $msg = "[{0}] pid={1} out={2}B err={3}B" -f (Get-Date -Format 'HH:mm:ss'), $p.Id, $outLen, $errLen
    if ($lastTarget) { $msg = $msg + " | " + $lastTarget }
    Write-Host $msg

    $nextStatus = (Get-Date).AddSeconds($StatusEverySeconds)
  }

  Start-Sleep -Seconds 1

  try {
    if ($p.HasExited) {
      Write-Host "Process exited early pid=$($p.Id)"
      break
    }
  } catch {}
}

try {
  if (-not $p.HasExited) {
    Stop-Process -Id $p.Id -Force
    Write-Host "Stopped pid=$($p.Id)"
  }
} catch {}
