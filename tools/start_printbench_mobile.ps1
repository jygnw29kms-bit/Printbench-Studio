param([switch]$StartCollector)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$collector=Join-Path $root 'tools\printbench_collector'
$ui=Join-Path $collector 'pi_ui'
$logDir=Join-Path $root 'runtime\mobile-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$python=(Get-Command python -ErrorAction Stop).Source
$cameraDir=Join-Path $root 'runtime\mobile-camera'
New-Item -ItemType Directory -Force -Path $cameraDir | Out-Null
$env:PRINTBENCH_CAMERA_SNAPSHOT=Join-Path $cameraDir 'latest.jpg'
if (-not (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)) {
    $env:PRINTBENCH_UI_HOST='0.0.0.0'
    $env:PRINTBENCH_UI_PORT='8080'
    $server=Start-Process -FilePath $python -ArgumentList @('-u','server.py') -WorkingDirectory $ui -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'ui.log') -RedirectStandardError (Join-Path $logDir 'ui-errors.log') -PassThru
    Write-Output "PRINTBENCH mobile server PID=$($server.Id)"
} else { Write-Output 'Mobile port 8080 already listening. Existing service retained.' }
if ($StartCollector) {
    $running=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '[p]ython.*[d]aemon.py' }
    if (-not $running) {
        # Explicit local-only mode: no external web push or spool cloud sync.
        $env:PRINTBENCH_P2S_CERT=Join-Path $env:LOCALAPPDATA 'PRINTBENCH\certs\p2s-cert.pem'
        $env:PRINTBENCH_WEB_PUSH='0'
        $env:PRINTBENCH_SPOOL_SYNC='0'
        $env:PRINTBENCH_MEDIA_WORKER='0'
        $env:PRINTBENCH_SLICER_SCAN='1'
        $proc=Start-Process -FilePath $python -ArgumentList @('-u','daemon.py') -WorkingDirectory $collector -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'collector.log') -RedirectStandardError (Join-Path $logDir 'collector-errors.log') -PassThru
        Write-Output "Local P2S collector PID=$($proc.Id)"
    } else {Write-Output 'Collector already running, retained.'}
}
# Camera bridge is strictly local; legacy media_worker is disabled above.
if (-not (Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match '[p]ython.*[c]amera_bridge.py'})) {
    $env:PRINTBENCH_CAMERA_RUNTIME=$cameraDir
    $cam=Start-Process -FilePath $python -ArgumentList @('-u','camera_bridge.py') -WorkingDirectory $collector -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'camera.log') -RedirectStandardError (Join-Path $logDir 'camera-errors.log') -PassThru
    Write-Output "Local camera bridge PID=$($cam.Id)"
}
# Windows can classify a trusted LAN as Public. Allow only LocalSubnet on
# both Windows profiles without exposing the UI beyond the local segment.
try {
    $rule = Get-NetFirewallRule -DisplayName 'PRINTBENCH Mobile LAN 8080' -ErrorAction SilentlyContinue
    if (-not $rule) {
        New-NetFirewallRule -DisplayName 'PRINTBENCH Mobile LAN 8080' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private,Public -RemoteAddress LocalSubnet | Out-Null
    } else {
        $rule | Set-NetFirewallRule -Profile Private,Public
    }
    Write-Output 'PRINTBENCH mobile firewall: Private/Public profile, TCP 8080, LocalSubnet only.'
} catch { Write-Warning 'Firewall rule requires administrator: phone access might be blocked.' }
Start-Sleep -Seconds 2
try { $r=Invoke-RestMethod 'http://127.0.0.1:8080/api/v1/capabilities' -TimeoutSec 5;Write-Output "Mobile API reachable: $($r.api), printer=$($r.printer)" }
catch {Write-Warning "Mobile API not ready: $_"}
