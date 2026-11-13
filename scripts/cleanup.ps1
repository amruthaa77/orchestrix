# cleanup.ps1 - Cleanup deployed resources or stop test cluster
param (
    [switch]$FullClusterTeardown
)

$RootDir = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $RootDir "bin"
if ($env:PATH -notmatch [regex]::Escape($BinDir)) {
    $env:PATH = "$BinDir;$env:PATH"
}
$K8sDir = Join-Path $RootDir "k8s"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Orchestrix Metrics: Cleanup                     " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

Write-Host "[*] Deleting Kubernetes deployment and service..." -ForegroundColor Yellow
& kubectl delete -f (Join-Path $K8sDir "deployment.yaml") --ignore-not-found
& kubectl delete -f (Join-Path $K8sDir "service.yaml") --ignore-not-found
& kubectl delete -f (Join-Path $K8sDir "hpa.yaml") --ignore-not-found

if ($FullClusterTeardown) {
    $minikubeCmd = Get-Command "minikube" -ErrorAction SilentlyContinue
    if ($minikubeCmd) {
        Write-Host "[*] Stopping Minikube cluster..." -ForegroundColor Yellow
        & minikube stop
    }
}

Write-Host "[+] Cleanup completed." -ForegroundColor Green
