param([switch]$StartCollector)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$collector=Join-Path $root 'tools\printbench_collector'
$ui=Join-Path $collector 'pi_ui'
$logDir=Join-Path $root 'runtime\mobile-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$python=(Get-Command python -ErrorAction Stop).Source
$secureDir=Join-Path $env:LOCALAPPDATA 'PRINTBENCH\mobile'
New-Item -ItemType Directory -Force -Path $secureDir | Out-Null
$env:PRINTBENCH_CONTROL_TOKEN_FILE=Join-Path $secureDir 'control.token'
$env:PRINTBENCH_CONTROL_AUDIT=Join-Path $secureDir 'control-audit.jsonl'
$env:PRINTBENCH_P2S_CERT=Join-Path $env:LOCALAPPDATA 'PRINTBENCH\certs\p2s-cert.pem'
$env:PRINTBENCH_CONTROL_WRITES='1'
$env:PRINTBENCH_CONTROL_DESTRUCTIVE='1'
$env:PRINTBENCH_CONTROL_THERMAL='1'
$env:PRINTBENCH_CONTROL_AMS='1'
$nic=Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.IPAddress -like '192.168.178.*'} | Select-Object -First 1
if ($nic) {$env:PRINTBENCH_LAN_IP=$nic.IPAddress}
Push-Location $ui
try {
    & $python -c 'import local_tls; local_tls.ensure_certificates(); import mobile_pairing; mobile_pairing.issue_pairing_code()' | Out-Null
} finally {Pop-Location}
if ($LASTEXITCODE -ne 0) { throw 'PRINTBENCH HTTPS setup failed; refusing insecure printer controls' }
$cameraDir=Join-Path $root 'runtime\mobile-camera'
New-Item -ItemType Directory -Force -Path $cameraDir | Out-Null
$env:PRINTBENCH_CAMERA_SNAPSHOT=Join-Path $cameraDir 'latest.jpg'
if (-not (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)) {
    $env:PRINTBENCH_UI_HOST='0.0.0.0'
    $env:PRINTBENCH_UI_PORT='8080'
    $server=Start-Process -FilePath $python -ArgumentList @('-u','server.py') -WorkingDirectory $ui -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'ui.log') -RedirectStandardError (Join-Path $logDir 'ui-errors.log') -PassThru
    Write-Output "PRINTBENCH mobile server PID=$($server.Id)"
} else { Write-Output 'Mobile port 8080 already listening. Existing service retained.' }
if (-not (Get-NetTCPConnection -LocalPort 8444 -State Listen -ErrorAction SilentlyContinue)) {
    $env:PRINTBENCH_UI_HOST='0.0.0.0'
    $env:PRINTBENCH_UI_PORT='8444'
    $env:PRINTBENCH_UI_TLS_CERT=Join-Path $secureDir 'server-cert.pem'
    $env:PRINTBENCH_UI_TLS_KEY=Join-Path $secureDir 'server-private.pem'
    $secureServer=Start-Process -FilePath $python -ArgumentList @('-u','server.py') -WorkingDirectory $ui -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'https.log') -RedirectStandardError (Join-Path $logDir 'https-errors.log') -PassThru
    Write-Output "PRINTBENCH secure mobile server PID=$($secureServer.Id)"
} else { Write-Output 'PRINTBENCH secure port 8444 already listening.' }
Remove-Item Env:PRINTBENCH_UI_TLS_CERT,Env:PRINTBENCH_UI_TLS_KEY -ErrorAction SilentlyContinue
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
    $httpsRule=Get-NetFirewallRule -DisplayName 'PRINTBENCH HTTPS Mobile LAN 8444' -ErrorAction SilentlyContinue
    if (-not $httpsRule) {
        New-NetFirewallRule -DisplayName 'PRINTBENCH HTTPS Mobile LAN 8444' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8444 -Profile Private,Public -RemoteAddress LocalSubnet | Out-Null
    } else { $httpsRule | Set-NetFirewallRule -Profile Private,Public }
    Write-Output 'PRINTBENCH mobile firewall: TCP 8080 read-only, TCP 8444 HTTPS authenticated control, LocalSubnet only.'
} catch { Write-Warning 'Firewall rule requires administrator: phone access might be blocked.' }
Start-Sleep -Seconds 2
try { $r=Invoke-RestMethod 'http://127.0.0.1:8080/api/v1/capabilities' -TimeoutSec 5;Write-Output "Mobile API reachable: $($r.api), printer=$($r.printer)" }
catch {Write-Warning "Mobile API not ready: $_"}
