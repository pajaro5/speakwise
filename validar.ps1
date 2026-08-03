Write-Host "`n=== Verificacion SpeakWise ===" -ForegroundColor Cyan
$ok = $true

# Docker
$dv = docker --version 2>$null
if ($dv) { Write-Host "OK Docker:       $dv" }
else      { Write-Host "FALLO Docker:       no disponible"; $ok = $false }

# Contenedor
$st = (docker compose ps --format "{{.Status}}" 2>$null)
if ($st -match "Up") { Write-Host "OK Contenedor:   running" }
else                       { Write-Host "FALLO Contenedor:   $st"; $ok = $false }

# API /health
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -EA Stop
    $body = $r.Content | ConvertFrom-Json
    if ($body.status -eq "ok") { Write-Host "OK API health:   ok" }
    else { Write-Host "FALLO API health:   respuesta inesperada: $($r.Content)"; $ok = $false }
} catch {
    Write-Host "FALLO API health:   no responde en :8000"; $ok = $false
}

# Frontend
try {
    $f = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing -EA Stop
    Write-Host "OK Frontend:     HTTP $($f.StatusCode)"
} catch {
    Write-Host "FALLO Frontend:     no responde en :8000/"; $ok = $false
}

# IP WiFi para movil
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notmatch "^127\."}
if ($ips) {
    $ips | ForEach-Object { Write-Host "OK Acceso movil: http://$($_.IPAddress):8000  [$($_.InterfaceAlias)]" }
} else {
    Write-Host "AVISO Red:          no se detecto IP - verificar conexion"
}

# pyproject.toml
if (Test-Path pyproject.toml) { Write-Host "OK pyproject:    existe" }
else                           { Write-Host "FALLO pyproject:    falta"; $ok = $false }

# Firewall
$fw = Get-NetFirewallRule -DisplayName "SpeakWise Dev" -ErrorAction SilentlyContinue
if ($fw -and $fw.Enabled -eq "True") { Write-Host "OK Firewall:     regla activa" }
else { Write-Host "AVISO Firewall:     regla no encontrada" }

# API Keys
$keys = Select-String -Path .env -Pattern "API_KEY=.+" -ErrorAction SilentlyContinue
if (($keys | Measure-Object).Count -ge 2) { Write-Host "OK API Keys:     completas" }
else { Write-Host "AVISO API Keys:     faltan completar en .env" }

Write-Host ""
if ($ok) { Write-Host "ENTORNO LISTO (Docker) - falta solo completar API keys si no lo hiciste" -ForegroundColor Green }
else      { Write-Host "HAY ERRORES - revisar los FALLO" -ForegroundColor Red }
Write-Host "==============================`n" -ForegroundColor Cyan
