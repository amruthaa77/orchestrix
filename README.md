# Orchestrix

Explainable Kubernetes rightsizing recommendations with Gemini explanations.
Built for Startup Buildathon India 2026.

## Status
- **Built:** local minikube test cluster (4 sample workloads), load generator, metrics capture
- **Prototype:** `optimizer.py` (rule-based recommender) and `explain.py` (Gemini explanations with a number check)
- **Planned:** seasonal forecasting, review and approval interface, guarded apply with audit trail and rollback, GKE deployment

Orchestrix recommends only. Nothing is applied to the cluster. Results come from about 8 minutes of synthetic load on a sample cluster and are not production benchmarks.

## How it works
1. `metrics.csv` holds captured CPU and memory samples for the sample workloads.
2. `optimizer.py` reads the current requests (live from kubectl when reachable) and recommends new requests: peak usage plus 50% headroom, with a 10m CPU and 32Mi memory minimum. An EWMA forecast is printed for reference and does not change the recommendation. It keeps the current request when no load was seen, or when a workload is bursty (peak at least 1.8x its average and at least 50% of its request).
3. `explain.py` sends the optimizer's summary output to Gemini (`gemini-4-hydrogen`), which explains each recommendation with risk and rollback. A check then confirms every number in the explanation appears in the engine output (presence, not placement). Gemini never sets values.

## Example result (sample cluster, per-workload CPU requests)
| Workload | Request | Peak seen | Recommended | Status |
|---|---|---|---|---|
| api-gateway | 500m | 0m | 500m | No load seen |
| batch-worker | 250m | 166m | 250m | Bursty, keep request |
| cache-redis | 200m | 9m | 15m | Over-provisioned |
| stateless-web-service | 100m | 14m | 25m | Over-provisioned |

Total: 1050m to 790m if all recommendations were applied (one replica per workload).

## Run the recommender
```powershell
pip install google-genai
python optimizer.py
$env:GEMINI_API_KEY = "your key from Google AI Studio"
$env:GEMINI_MODEL = "gemini-4-hydrogen"
python optimizer.py | python explain.py
```
Never commit an API key.

## Known limitations
- Short, synthetic sample: the p95 equals the peak on this data, and the EWMA forecast does not affect recommendations yet.
- Samples are short-window averages from metrics-server, so brief bursts can be hidden.
- Recommendations are advisory. Validate in staging before applying.

## Local test environment
Scripts to bootstrap a local Minikube or Kind cluster, deploy the sample workloads, and generate traffic.

```
k8s/         deployment.yaml, service.yaml, hpa.yaml (sample web service with explicit requests and limits)
traffic/     locustfile.py, traffic_benchmark.py, requirements.txt, run_locust.ps1
scripts/     setup_cluster.ps1, deploy.ps1, port_forward.ps1, cleanup.ps1
workloads.yaml, metrics.csv, optimizer.py, explain.py
```

```powershell
.\scripts\setup_cluster.ps1 -ClusterType minikube
.\scripts\deploy.ps1
.\scripts\port_forward.ps1
python -m pip install -r .\traffic\requirements.txt
.\traffic\run_locust.ps1 -HostUrl "http://localhost:8080" -Users 20 -SpawnRate 5 -RunTime "30s"
```

The traffic benchmark script (`traffic/traffic_benchmark.py`) is a hey-style CLI generator, for example `python .\traffic\traffic_benchmark.py -n 500 -c 20 http://localhost:8080/`. Its output format is shown for illustration only.

Teardown: `.\scripts\cleanup.ps1` (add `-FullClusterTeardown` to stop the cluster).
