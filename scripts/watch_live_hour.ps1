param(
  [Parameter(Mandatory=$true)][string]$Path,
  [int]$Targeting = 10,
  [int]$Tail = 40
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Path)) {
  throw "Log not found: $Path"
}

"--- file ---"
$Path
"--- targeting (last $Targeting) ---"
Select-String -Path $Path -Pattern "\[fenril\]\[info\] targeting:" | Select-Object -Last $Targeting | ForEach-Object { $_.Line }
"--- click sent (last 5) ---"
Select-String -Path $Path -Pattern "input: attack click sent backend" | Select-Object -Last 5 | ForEach-Object { $_.Line }
"--- tail (last $Tail) ---"
Get-Content -Path $Path -Tail $Tail
