# deploy.ps1 - Deploy stateless web service with explicit CPU/Memory requests
$RootDir = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $RootDir "bin"
if ($env:PATH -notmatch [regex]::Escape($BinDir)) {
    $env:PATH = "$BinDir;$env:PATH"
}

$K8sDir = Join-Path $RootDir "k8s"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Orchestrix Metrics: Deploying Web Service       " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Apply Deployment
Write-Host "[*] Applying Deployment with explicit CPU and Memory requests..." -ForegroundColor Yellow
& kubectl apply -f (Join-Path $K8sDir "deployment.yaml")

# 2. Apply Service
Write-Host "[*] Applying Service..." -ForegroundColor Yellow
& kubectl apply -f (Join-Path $K8sDir "service.yaml")

# 3. Wait for rollout
Write-Host "[*] Waiting for deployment rollout to complete..." -ForegroundColor Yellow
& kubectl rollout status deployment/stateless-web-service --timeout=120s

# 4. Show Pods and explicit resource requests
Write-Host "[+] Active Pods:" -ForegroundColor Green
& kubectl get pods -l app=stateless-web-service -o wide

Write-Host "`n[+] Pod Resource Requests & Limits Configuration:" -ForegroundColor Green
& kubectl get deployment stateless-web-service -o jsonpath="{range .spec.template.spec.containers[*]}Container: {.name}{'\n'}  CPU Request:    {.resources.requests.cpu}{'\n'}  Memory Request: {.resources.requests.memory}{'\n'}  CPU Limit:      {.resources.limits.cpu}{'\n'}  Memory Limit:   {.resources.limits.memory}{'\n'}{end}"

Write-Host "`n[+] Service Details:" -ForegroundColor Green
& kubectl get service stateless-web-service
