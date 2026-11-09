param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$ui=Join-Path $root 'tools\printbench_collector\pi_ui'
$python=(Get-Command python -ErrorAction Stop).Source
Push-Location $ui
try {
    $json=& $python -c 'import json,mobile_pairing;print(json.dumps(mobile_pairing.ensure_pairing_code()))'
    if ($LASTEXITCODE -ne 0) { throw 'Kopplungscode konnte nicht erzeugt werden.' }
    $pin=$json | ConvertFrom-Json
} finally { Pop-Location }
if ($pin.code -notmatch '^[0-9]{8}$'){throw 'Kopplungscode konnte nicht erzeugt werden.'}
Add-Type -AssemblyName PresentationFramework
$nl=[Environment]::NewLine
$expires=[DateTimeOffset]::FromUnixTimeSeconds([int64]$pin.expires_at).ToLocalTime()
$expiryMessage='Gültig bis '+$expires.ToString('HH:mm:ss')+' Uhr, nur einmal verwendbar.'
$certificate=Join-Path $env:LOCALAPPDATA 'PRINTBENCH\mobile\ca.cer'
$fingerprint=if(Test-Path -LiteralPath $certificate){(Get-FileHash -Algorithm SHA256 -LiteralPath $certificate).Hash}else{'Zertifikat nicht gefunden'}
$message='PRINTBENCH iPhone-Kopplung'+$nl+$nl+'Code: '+$pin.code+$nl+$nl+$expiryMessage+$nl+'In der HTTPS-App unter Sicherheit eingeben.'+$nl+$nl+'PRINTBENCH CA SHA256:'+$nl+$fingerprint
[System.Windows.MessageBox]::Show($message,'PRINTBENCH iPhone koppeln',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Information) | Out-Null
