$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$launcher=Join-Path $PSScriptRoot 'start_printbench_mobile.ps1'
$startup=[Environment]::GetFolderPath('Startup')
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
$pairing=Join-Path $PSScriptRoot 'show_printbench_mobile_pairing.ps1'
$pairingShortcut=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\PRINTBENCH iPhone koppeln.lnk'
$pairLink=$shell.CreateShortcut($pairingShortcut)
$pairLink.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$pairLink.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$pairing+'"'
$pairLink.WorkingDirectory=$root
$pairLink.Description='Einmaligen iPhone-Kopplungscode für PRINTBENCH anzeigen'
$pairLink.Save()
New-Item -ItemType Directory -Force -Path (Join-Path $env:LOCALAPPDATA 'PRINTBENCH\mobile\uploads') | Out-Null
$fileShortcut=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\PRINTBENCH iPhone Dateien.lnk'
$fileLink=$shell.CreateShortcut($fileShortcut)
$fileLink.TargetPath='explorer.exe'
$fileLink.Arguments='"'+(Join-Path $env:LOCALAPPDATA 'PRINTBENCH\mobile\uploads')+'"'
$fileLink.WorkingDirectory=$root
$fileLink.Description='Vom iPhone an PRINTBENCH übertragene Druckdateien'
$fileLink.Save()
$queueScript=Join-Path $PSScriptRoot 'printbench_mobile_inbox.py'
$queueLink=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\PRINTBENCH Druckwarteliste.lnk'))
$queueLink.TargetPath=(Get-Command pythonw -ErrorAction Stop).Source
$queueLink.Arguments='"'+$queueScript+'"'
$queueLink.WorkingDirectory=$root
$queueLink.Description='iPhone-Dateien im nativen PRINTBENCH-Slicer öffnen'
$queueLink.Save()
Write-Output 'PRINTBENCH mobile autostart, pairing, uploaded files and desktop queue shortcuts installed.'
