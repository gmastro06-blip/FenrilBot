param(
  [Parameter(Mandatory=$true, ParameterSetName='ByColor')]
  [ValidateSet('Green','Red','Golden')]
  [string]$Color,

  [Parameter(Mandatory=$true, ParameterSetName='ByName')]
  [string]$Name
)

$ErrorActionPreference = 'Stop'

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'

if ($PSCmdlet.ParameterSetName -eq 'ByName') {
  $out = "src/repositories/inventory/images/slots/$Name v2.png"
  $label = $Name
} else {
  $out = "src/repositories/inventory/images/slots/$Color Backpack v2.png"
  $label = "$Color Backpack"
}

Write-Host "Copy the $label ICON (inventory slot) image to clipboard, then run this script." -ForegroundColor Cyan
Write-Host "Saving to: $out" -ForegroundColor Cyan

& $python scripts/save_clipboard_template.py --out "$out" --force

Write-Host "Done. Verifying file exists..." -ForegroundColor Cyan
Test-Path $out
