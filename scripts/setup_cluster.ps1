# setup_cluster.ps1 - Bootstrap local Kubernetes test environment (Minikube / Kind)
param (
    [ValidateSet("minikube", "kind")]
    [string]$ClusterType = "minikube",
    [string]$Driver = "docker"
)

$RootDir = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $RootDir "bin"
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

# Ensure bin is in current process PATH
if ($env:PATH -notmatch [regex]::Escape($BinDir)) {
    $env:PATH = "$BinDir;$env:PATH"
}

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Orchestrix Metrics: Kubernetes Cluster Setup    " -ForegroundColor Cyan
Write-Host " Target Cluster: $ClusterType | Driver: $Driver " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Ensure kubectl is available
$kubectlCmd = Get-Command "kubectl" -ErrorAction SilentlyContinue
if (-not $kubectlCmd) {
    $kubectlPath = Join-Path $BinDir "kubectl.exe"
    if (-not (Test-Path $kubectlPath)) {
        Write-Host "[*] Downloading kubectl CLI to $kubectlPath ..." -ForegroundColor Yellow
        $kubectlUrl = "https://dl.k8s.io/release/v1.30.0/bin/windows/amd64/kubectl.exe"
        curl.exe -L $kubectlUrl -o $kubectlPath
    }
    Write-Host "[+] kubectl binary ready at: $kubectlPath" -ForegroundColor Green
} else {
    Write-Host "[+] Found kubectl at: $($kubectlCmd.Source)" -ForegroundColor Green
}

# 2. Check cluster tool (Minikube or Kind)
if ($ClusterType -eq "minikube") {
    $minikubeCmd = Get-Command "minikube" -ErrorAction SilentlyContinue
    if (-not $minikubeCmd) {
        $minikubePath = Join-Path $BinDir "minikube.exe"
        if (-not (Test-Path $minikubePath)) {
            Write-Host "[*] Downloading minikube to $minikubePath ..." -ForegroundColor Yellow
            $minikubeUrl = "https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe"
            curl.exe -L $minikubeUrl -o $minikubePath
        }
        Write-Host "[+] minikube binary ready at: $minikubePath" -ForegroundColor Green
    } else {
        Write-Host "[+] Found minikube at: $($minikubeCmd.Source)" -ForegroundColor Green
    }

    # Verify container engine / driver
    Write-Host "[*] Checking container driver ($Driver)..." -ForegroundColor Yellow
    $dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
    if (-not $dockerCmd -and $Driver -eq "docker") {
        Write-Host "[!] Docker CLI was not detected on PATH." -ForegroundColor Yellow
        Write-Host "[!] If Docker Desktop is installed, please ensure it is running." -ForegroundColor Yellow
        Write-Host "[!] Alternatively, install Docker Desktop via winget: winget install Docker.DockerDesktop" -ForegroundColor Yellow
    }

    Write-Host "[*] Starting Minikube cluster (driver: $Driver)..." -ForegroundColor Yellow
    & minikube start --driver=$Driver --cpus=2 --memory=2048

    Write-Host "[*] Enabling metrics-server addon in Minikube..." -ForegroundColor Yellow
    & minikube addons enable metrics-server

    Write-Host "[+] Minikube cluster status:" -ForegroundColor Green
    & minikube status

} elseif ($ClusterType -eq "kind") {
    $kindCmd = Get-Command "kind" -ErrorAction SilentlyContinue
    if (-not $kindCmd) {
        $kindPath = Join-Path $BinDir "kind.exe"
        if (-not (Test-Path $kindPath)) {
            Write-Host "[*] Downloading kind to $kindPath ..." -ForegroundColor Yellow
            $kindUrl = "https://kind.sigs.k8s.io/dl/v0.23.0/kind-windows-amd64.exe"
            curl.exe -L $kindUrl -o $kindPath
        }
        Write-Host "[+] kind binary ready at: $kindPath" -ForegroundColor Green
    } else {
        Write-Host "[+] Found kind at: $($kindCmd.Source)" -ForegroundColor Green
    }

    Write-Host "[*] Creating Kind cluster (cluster-name: test-cluster)..." -ForegroundColor Yellow
    & kind create cluster --name test-cluster
}

Write-Host "[+] Verifying cluster nodes:" -ForegroundColor Green
& kubectl get nodes
