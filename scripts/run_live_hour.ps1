param(
  [int]$Seconds = 3600,
  [string]$Tag = ""
)

$ErrorActionPreference = 'Stop'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
if ([string]::IsNullOrWhiteSpace($Tag)) {
  $tagPart = ""
} else {
  $tagPart = "_${Tag}".Replace(' ', '_')
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$debugDir = Join-Path $repoRoot 'debug'
New-Item -ItemType Directory -Force -Path $debugDir | Out-Null

$out = Join-Path $debugDir "live_hour${tagPart}_${ts}.out.log"
$err = Join-Path $debugDir "live_hour${tagPart}_${ts}.err.log"
$meta = Join-Path $debugDir "live_hour${tagPart}_${ts}.meta.json"
$pidPath = Join-Path $debugDir "live_hour${tagPart}_${ts}.pid.txt"

$python = (Resolve-Path (Join-Path $repoRoot '.venv\Scripts\python.exe')).Path
$wd = $repoRoot

# NOTE: These env vars were validated in previous runs.
$envs = @{
  FENRIL_ATTACK_FROM_BATTLELIST = '1'
  FENRIL_DISABLE_ARDUINO_CLICKS = '1'
  FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER = 'ctrl'
  FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK = '1'
  FENRIL_FOCUS_AFTER_S = '0.05'
  FENRIL_INPUT_DIAG = '1'
  FENRIL_TARGETING_DIAG = '1'
}

# Run the bot for N seconds, then stop it.
$job = Start-Job -Name "fenril_live_hour_${ts}" -ScriptBlock {
  param($python, $wd, $out, $err, $pidPath, $seconds, $envs)

  foreach ($k in $envs.Keys) {
    Set-Item -Path ("Env:{0}" -f $k) -Value $envs[$k]
  }

  "started at $(Get-Date -Format o)" | Add-Content -Encoding UTF8 -LiteralPath $out
  $p = Start-Process -FilePath $python -ArgumentList @('-u','main.py') -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
  try { Set-Content -Encoding ASCII -LiteralPath $pidPath -Value $p.Id } catch {}
  Start-Sleep -Seconds $seconds
  try { Stop-Process -Id $p.Id -Force } catch {}
  "stopped pid=$($p.Id)"
} -ArgumentList $python, $wd, $out, $err, $pidPath, $Seconds, $envs

@{
  ts = $ts
  tag = $Tag
  seconds = $Seconds
  jobId = $job.Id
  jobName = $job.Name
  out = $out
  err = $err
  pidPath = $pidPath
  env = $envs
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $meta

"STARTED jobId=$($job.Id) seconds=$Seconds"
"OUT=$out"
"ERR=$err"
"META=$meta"
"To watch:  .\\scripts\\watch_live_hour.ps1 -Path '$out'"
"To stop now: Stop-Job -Id $($job.Id); Receive-Job -Id $($job.Id) -Keep"
