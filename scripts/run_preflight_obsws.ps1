# Preflight using OBS WebSocket capture.

$ErrorActionPreference = 'Stop'

$env:FENRIL_CAPTURE_BACKEND = 'obsws'
$env:FENRIL_OBS_SOURCE = 'Tibia_Fuente'
$env:FENRIL_OBS_HOST = '127.0.0.1'
$env:FENRIL_OBS_PORT = '4455'

$python = 'C:/Users/gmast/AppData/Local/Programs/Python/Python312/python.exe'
& $python (Join-Path $PSScriptRoot 'preflight_dual_windows.py')
