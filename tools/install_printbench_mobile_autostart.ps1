$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$launcher=Join-Path $PSScriptRoot 'start_printbench_mobile.ps1'
$startup='C:\Users\dezen\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup'
New-Item -ItemType Directory -Force -Path $startup | Out-Null
$shortcut=Join-Path $startup 'PRINTBENCH Mobile LAN.lnk'
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($shortcut)
$link.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$link.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$launcher+'" -StartCollector'
$link.WorkingDirectory=$root
$link.WindowStyle=7
$link.Description='PRINTBENCH iPhone LAN App and local P2S telemetry'
$link.Save()
if(-not (Test-Path $shortcut)){throw 'Startup shortcut not created'}
Write-Output "PRINTBENCH mobile autostart installed: $shortcut"
