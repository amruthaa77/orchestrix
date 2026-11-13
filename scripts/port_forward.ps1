# port_forward.ps1 - Forward local port 8080 to stateless-web-service
param (
    [int]$LocalPort = 8080,
    [int]$RemotePort = 80
)

$RootDir = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $RootDir "bin"
if ($env:PATH -notmatch [regex]::Escape($BinDir)) {
    $env:PATH = "$BinDir;$env:PATH"
}

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Orchestrix Metrics: Port Forwarding             " -ForegroundColor Cyan
Write-Host " Forwarding localhost:$LocalPort -> svc:stateless-web-service:$RemotePort" -ForegroundColor Green
Write-Host " Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Cyan

& kubectl port-forward service/stateless-web-service ${LocalPort}:${RemotePort}
