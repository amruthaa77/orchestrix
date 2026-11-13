"""
Orchestrix optimizer (Phase 1 prototype): rule-based right-sizing with a
baseline EWMA forecast. It RECOMMENDS only; it never changes the cluster.

Usage (PowerShell, from the project folder):
    python optimizer.py                 # reads metrics.csv, asks kubectl for live requests
    python optimizer.py metrics.csv

Requests are read live from `kubectl get pods -o json`. If kubectl is not
reachable, it falls back to FALLBACK_REQUESTS (values from workloads.yaml)
and says so in the output.
"""
import csv, json, math, os, re, subprocess, sys
from collections import defaultdict

HEADROOM_CPU = 1.50     # 50% above the busiest recent level
HEADROOM_MEM = 1.50     # memory is not compressible, so more margin
MIN_CPU_M, MIN_MEM_MI = 10, 32
NO_LOAD_M = 2           # peak at or below this => no meaningful load seen
BURSTY_RATIO = 1.8      # peak / average above this => bursty
EWMA_ALPHA = 0.3

FALLBACK_REQUESTS = {   # (cpu millicores, memory MiB) as set in workloads.yaml
    "stateless-web-service": (100, 128),
    "api-gateway": (500, 512),
    "cache-redis": (200, 512),
    "batch-worker": (250, 256),
}

def workload_name(pod):
    return re.sub(r"-[a-z0-9]{8,10}-[a-z0-9]{5}$", "", pod)

def to_cpu_m(v):
    v = str(v).strip()
    return int(float(v[:-1])) if v.endswith("m") else int(float(v) * 1000)

def to_mem_mi(v):
    v = str(v).strip()
    for suf, f in (("Ki", 1/1024), ("Mi", 1), ("Gi", 1024)):
        if v.endswith(suf):
            return int(float(v[:-2]) * f)
    return int(float(v) / (1024 * 1024))

def requests_from_kubectl_json(data):
    out = {}
    for item in data.get("items", []):
        wl = workload_name(item["metadata"]["name"])
        cpu = mem = 0
        for c in item["spec"]["containers"]:
            r = c.get("resources", {}).get("requests", {})
            cpu += to_cpu_m(r.get("cpu", "0"))
            mem += to_mem_mi(r.get("memory", "0"))
        out[wl] = (cpu, mem)
    return out

def get_requests():
    kubectl = os.path.join("bin", "kubectl.exe")
    kubectl = kubectl if os.path.exists(kubectl) else "kubectl"
    try:
        raw = subprocess.run([kubectl, "get", "pods", "-o", "json"],
                             capture_output=True, text=True, timeout=15, check=True).stdout
        reqs = requests_from_kubectl_json(json.loads(raw))
        if reqs:
            return reqs, "live from kubectl"
    except Exception:
        pass
    return FALLBACK_REQUESTS, "FALLBACK values from workloads.yaml (kubectl not reachable)"

def pct(values, p):
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1)]

def ewma(values, a=EWMA_ALPHA):
    f = values[0]
    for v in values[1:]:
        f = a * v + (1 - a) * f
    return f

def round_up(x, step=5):
    return int(math.ceil(x / step) * step)

def load(csv_file):
    cpu, mem = defaultdict(list), defaultdict(list)
    with open(csv_file, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                c = int(row["cpu"].replace("m", "").strip())
                m = int(row["mem"].replace("Mi", "").strip())
            except (ValueError, AttributeError, KeyError):
                continue
            wl = workload_name(row["pod"])
            cpu[wl].append(c); mem[wl].append(m)
    return cpu, mem

def analyze(csv_file="metrics.csv"):
    """Return (records, requests_source). Pure computation, no printing."""
    reqs, source = get_requests()
    cpu, mem = load(csv_file)
    records = []
    for wl in sorted(cpu):
        if wl not in reqs:
            continue
        req_c, req_m = reqs[wl]
        c, m = cpu[wl], mem[wl]
        peak, avg, p95, fc = max(c), sum(c) / len(c), pct(c, 95), ewma(c)
        mpeak = max(m)
        util = peak / req_c if req_c else 0
        bursty = avg > 0 and peak / avg >= BURSTY_RATIO and util >= 0.5
        note = ""
        if peak <= NO_LOAD_M:
            status, risk, rec_c = "NO LOAD SEEN", "unknown", req_c
            note = "No meaningful load in this window. Keep the request until real load is observed."
        elif bursty:
            status, risk, rec_c = "BURSTY", "medium", req_c
            note = ("Samples are ~60 s averages, so short bursts are hidden. "
                    "Do not shrink from averages; collect finer-grained data first.")
        else:
            base = max(p95, fc, peak)
            rec_c = max(MIN_CPU_M, round_up(base * HEADROOM_CPU))
            status = "OVER-PROVISIONED" if util < 0.25 else ("AT RISK" if util > 0.8 else "OK")
            risk = "low" if status == "OVER-PROVISIONED" else "medium"
            rec_c = min(rec_c, req_c) if status == "OVER-PROVISIONED" else rec_c
        rec_m = max(MIN_MEM_MI, round_up(mpeak * HEADROOM_MEM, 8))
        rec_m = min(rec_m, req_m)
        if peak <= NO_LOAD_M or bursty:
            rec_m = req_m   # no load seen, or bursty: do not shrink memory either
        records.append(dict(
            workload=wl, status=status, risk=risk, note=note,
            cpu_request_m=req_c, cpu_recommended_m=rec_c,
            mem_request_mi=req_m, mem_recommended_mi=rec_m,
            cpu_peak_m=peak, cpu_p95_m=p95, cpu_avg_m=round(avg),
            cpu_forecast_m=round(fc), mem_peak_mi=mpeak,
            cpu_cut_pct=round(100 * (req_c - rec_c) / req_c) if req_c else 0))
    return records, source

def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "metrics.csv"
    if not os.path.exists(csv_file):
        sys.exit(f"{csv_file} not found. Run the metrics capture first.")
    records, source = analyze(csv_file)
    print("--- Orchestrix Optimizer (recommendations only) ---")
    print(f"Requests source: {source}\n")
    tot_req = tot_rec = 0
    for r in records:
        tot_req += r["cpu_request_m"]; tot_rec += r["cpu_recommended_m"]
        print(f"Workload: {r['workload']}")
        print(f"  Status: {r['status']}   Risk: {r['risk']}")
        print(f"  CPU    request {r['cpu_request_m']}m | peak {r['cpu_peak_m']}m, p95 {r['cpu_p95_m']}m, "
              f"avg {r['cpu_avg_m']}m, EWMA forecast {r['cpu_forecast_m']}m "
              f"-> recommended request {r['cpu_recommended_m']}m")
        print(f"  Memory request {r['mem_request_mi']}Mi | peak {r['mem_peak_mi']}Mi "
              f"-> recommended request {r['mem_recommended_mi']}Mi")
        if r["note"]: print(f"  Note: {r['note']}")
        print()
    print(f"CPU requests across listed workloads: {tot_req}m -> {tot_rec}m if all applied")
    print("Recommendations only. Nothing was applied to the cluster.")

if __name__ == "__main__":
    main()