param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$ui=Join-Path $root 'tools\printbench_collector\pi_ui'
$python=(Get-Command python -ErrorAction Stop).Source
Push-Location $ui
try {
    $code=& $python -c 'import mobile_pairing;print(mobile_pairing.ensure_pairing_code())'
} finally { Pop-Location }
if ($LASTEXITCODE -ne 0 -or $code -notmatch '^[0-9]{8}$'){throw 'Kopplungscode konnte nicht erzeugt werden.'}
Add-Type -AssemblyName PresentationFramework
$nl=[Environment]::NewLine
# A reused one-time PIN may have fewer than 15 minutes remaining.
# Show the actual expiry and never rotate a valid code just to open this window.
$pinFile=Join-Path $env:LOCALAPPDATA 'PRINTBENCH\mobile\pairing.code'
$expiryMessage='Gültigkeit nicht ermittelbar'
try {
    $expiryUnix=[int64]((Get-Content -LiteralPath $pinFile -Raw -ErrorAction Stop).Split(':')[0])
    $expires=[DateTimeOffset]::FromUnixTimeSeconds($expiryUnix).ToLocalTime()
    $remaining=[Math]::Max(0,[Math]::Ceiling(($expires-[DateTimeOffset]::Now).TotalMinutes))
    $expiryMessage='Noch '+$remaining+' Min. gültig (bis '+$expires.ToString('HH:mm:ss')+'), nur einmal verwendbar.'
} catch {}
$certificate=Join-Path $ui 'static\PRINTBENCH-Local-CA.cer'
$fingerprint=if(Test-Path $certificate){(Get-FileHash -Algorithm SHA256 -Path $certificate).Hash}else{'Zertifikat nicht gefunden'}
$message='PRINTBENCH iPhone-Kopplung'+$nl+$nl+'Code: '+$code+$nl+$nl+$expiryMessage+$nl+'In der HTTPS-App unter Sicherheit eingeben.'+$nl+$nl+'PRINTBENCH CA SHA256:'+$nl+$fingerprint
[System.Windows.MessageBox]::Show($message,'PRINTBENCH iPhone koppeln',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Information) | Out-Null
$code=$null
