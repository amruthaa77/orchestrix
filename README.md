# Orchestrix Metrics - Local Kubernetes & Traffic Generation Environment

This repository provides an automated local Kubernetes test environment setup (using **Minikube** or **Kind**), a sample stateless web service configured with explicit CPU and memory requests, and high-performance traffic generation scripts powered by **Locust** and a **hey**-compatible benchmark tool.

---

## 📁 Repository Structure

```
c:\projects\orchestrix-metrics\
├── bin\                          # Downloaded CLI utilities (kubectl, minikube, kind)
├── k8s\
│   ├── deployment.yaml           # Stateless web service with explicit CPU & Memory requests
│   ├── service.yaml              # NodePort/ClusterIP service definition
│   └── hpa.yaml                  # Horizontal Pod Autoscaler (optional CPU-based autoscaling)
├── traffic\
│   ├── locustfile.py             # Locust user simulation script
│   ├── traffic_benchmark.py      # Async high-concurrency CLI traffic generator (hey equivalent)
│   ├── requirements.txt          # Python load testing dependencies
│   └── run_locust.ps1            # Convenience runner for Locust (Headless & Web UI)
├── scripts\
│   ├── setup_cluster.ps1         # Bootstraps local Minikube or Kind cluster
│   ├── deploy.ps1                # Deploys K8s manifests & checks resource requests
│   ├── port_forward.ps1          # Forwards localhost:8080 to the web service
│   └── cleanup.ps1               # Cleans up deployed resources
└── README.md
```

---

## ⚙️ 1. Kubernetes Resource Configuration

The sample stateless web service is defined in [`k8s/deployment.yaml`](file:///c:/projects/orchestrix-metrics/k8s/deployment.yaml) with explicit resource requests and limits:

```yaml
resources:
  requests:
    cpu: "100m"          # 0.1 CPU core reserved per pod
    memory: "128Mi"      # 128 Megabytes RAM reserved per pod
  limits:
    cpu: "500m"          # Up to 0.5 CPU core burst limit
    memory: "256Mi"      # 256 Megabytes RAM upper limit
```

- **Replicas:** 2 stateless pods (`nginx:alpine`)
- **Probes:** Configured with HTTP `readinessProbe` and `livenessProbe` for zero-downtime traffic handling.
- **Service:** Defined in [`k8s/service.yaml`](file:///c:/projects/orchestrix-metrics/k8s/service.yaml) exposing port 80.

---

## 🚀 2. Getting Started

### Step 2.1: Bootstrap the Cluster

Ensure Docker Desktop or WSL2 is installed and running, then execute:

```powershell
# Default: bootstraps Minikube with Docker driver and downloads kubectl
.\scripts\setup_cluster.ps1 -ClusterType minikube

# Or to use Kind:
.\scripts\setup_cluster.ps1 -ClusterType kind
```

### Step 2.2: Deploy the Web Service

Deploy the stateless web service and verify explicit resource configurations:

```powershell
.\scripts\deploy.ps1
```

This will output the running pods along with confirmation of the CPU and memory requests:
```text
Container: web-app
  CPU Request:    100m
  Memory Request: 128Mi
  CPU Limit:      500m
  Memory Limit:   256Mi
```

### Step 2.3: Forward Traffic to Localhost

Expose the service on `http://localhost:8080`:

```powershell
.\scripts\port_forward.ps1
```

---

## 🚦 3. Generating Traffic

You have two traffic generation tools ready out of the box:

### Option A: Locust Traffic Generator

Install dependencies:
```powershell
python -m pip install -r .\traffic\requirements.txt
```

#### Run in Headless CLI Mode (automated 30-second run with 20 users):
```powershell
.\traffic\run_locust.ps1 -HostUrl "http://localhost:8080" -Users 20 -SpawnRate 5 -RunTime "30s"
```

#### Run with Locust Web UI:
```powershell
.\traffic\run_locust.ps1 -HostUrl "http://localhost:8080" -WebUI
```
Open **[http://localhost:8089](http://localhost:8089)** in your browser to view real-time latency graphs, RPS meters, and error charts.

---

### Option B: Fast Concurrent CLI Generator (`hey` equivalent)

[`traffic/traffic_benchmark.py`](file:///c:/projects/orchestrix-metrics/traffic/traffic_benchmark.py) provides high-performance async benchmarking mimicking `rakyll/hey`:

```powershell
# Send 500 requests across 20 concurrent workers
python .\traffic\traffic_benchmark.py -n 500 -c 20 http://localhost:8080/

# Or run continuously for 30 seconds with 15 concurrent workers
python .\traffic\traffic_benchmark.py -z 30s -c 15 http://localhost:8080/
```

**Sample Output:**
```text
Summary:
  Total time:        1.4231 secs
  Total requests:    500
  Slowest:           0.0821 secs
  Fastest:           0.0124 secs
  Average:           0.0381 secs
  Requests/sec:      351.34
  Concurrency:       20

Latency distribution:
  10% in 0.0210 secs
  50% in 0.0350 secs
  90% in 0.0580 secs
  99% in 0.0780 secs

Status code distribution:
  [HTTP 200] 500 responses
```

---

## 🧹 4. Teardown

To delete the deployment and service:
```powershell
.\scripts\cleanup.ps1
```

To also stop the local Minikube cluster:
```powershell
.\scripts\cleanup.ps1 -FullClusterTeardown
```
