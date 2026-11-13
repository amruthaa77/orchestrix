# run_locust.ps1 - Run Locust traffic generator for the stateless web service
param (
    [string]$HostUrl = "http://localhost:8080",
    [int]$Users = 20,
    [int]$SpawnRate = 5,
    [string]$RunTime = "30s",
    [switch]$WebUI
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$LocustFile = Join-Path $ScriptDir "locustfile.py"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Orchestrix Metrics: Locust Traffic Generator   " -ForegroundColor Cyan
Write-Host " Target URL: $HostUrl" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan

# Ensure dependencies installed
Write-Host "[*] Checking Python Locust dependency..." -ForegroundColor Yellow
python -m pip install -q -r (Join-Path $ScriptDir "requirements.txt")

if ($WebUI) {
    Write-Host "[*] Launching Locust with Web UI on http://localhost:8089 ..." -ForegroundColor Green
    locust -f $LocustFile --host $HostUrl
} else {
    Write-Host "[*] Launching Locust in Headless Mode ($Users users, $SpawnRate/sec, duration $RunTime)..." -ForegroundColor Green
    locust -f $LocustFile --host $HostUrl --headless -u $Users -r $SpawnRate --run-time $RunTime --csv "$ScriptDir\locust_report"
    Write-Host "[+] Traffic test finished. CSV reports generated at $ScriptDir\locust_report_*.csv" -ForegroundColor Green
}
