#!/usr/bin/env python3
"""
traffic_benchmark.py - A lightweight, high-performance HTTP load generator matching rakyll/hey.

Usage:
    python traffic_benchmark.py -n 1000 -c 20 http://localhost:8080/
    python traffic_benchmark.py -z 30s -c 10 http://localhost:8080/
"""

import argparse
import asyncio
import sys
import time
from collections import Counter
from typing import List, Tuple
import httpx

def parse_duration(duration_str: str) -> float:
    """Parse duration string like '30s', '2m', '500ms' into seconds."""
    duration_str = duration_str.strip().lower()
    if duration_str.endswith("ms"):
        return float(duration_str[:-2]) / 1000.0
    elif duration_str.endswith("s"):
        return float(duration_str[:-1])
    elif duration_str.endswith("m"):
        return float(duration_str[:-1]) * 60.0
    return float(duration_str)

async def worker(
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    results: List[Tuple[int, float, str]],
    stop_event: asyncio.Event,
):
    """Worker task sending requests until queue is empty or stop_event is set."""
    while not stop_event.is_set():
        try:
            # Non-blocking get with timeout to check stop_event
            if queue is not None:
                try:
                    await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if queue.empty():
                        break
                    continue
            start_t = time.perf_counter()
            resp = await client.request(method, url)
            elapsed = time.perf_counter() - start_t
            results.append((resp.status_code, elapsed, ""))
            if queue is not None:
                queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            elapsed = time.perf_counter() - start_t if 'start_t' in locals() else 0.0
            results.append((0, elapsed, str(e)))
            if queue is not None:
                queue.task_done()

async def run_benchmark(
    url: str,
    method: str = "GET",
    num_requests: int = 200,
    concurrency: int = 20,
    duration_seconds: float = None,
):
    print(f"\nRunning benchmark against: {url}")
    if duration_seconds:
        print(f"Duration: {duration_seconds}s | Concurrency: {concurrency}")
    else:
        print(f"Requests: {num_requests} | Concurrency: {concurrency}")
    print("--------------------------------------------------")

    results: List[Tuple[int, float, str]] = []
    stop_event = asyncio.Event()

    queue = asyncio.Queue() if duration_seconds is None else None
    if queue is not None:
        for _ in range(num_requests):
            queue.put_nowait(1)

    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(10.0, connect=5.0)

    start_total = time.perf_counter()
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        workers = [
            asyncio.create_task(worker(queue, client, method, url, results, stop_event))
            for _ in range(concurrency)
        ]

        if duration_seconds is not None:
            await asyncio.sleep(duration_seconds)
            stop_event.set()
        else:
            await queue.join()
            stop_event.set()

        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    total_time = time.perf_counter() - start_total
    print_summary(results, total_time, concurrency)

def print_summary(results: List[Tuple[int, float, str]], total_time: float, concurrency: int):
    if not results:
        print("No requests completed.")
        return

    durations = [r[1] for r in results if r[0] > 0]
    durations.sort()
    status_codes = Counter(r[0] for r in results)
    errors = [r[2] for r in results if r[0] == 0]

    total_done = len(results)
    successful = len(durations)
    rps = total_done / total_time if total_time > 0 else 0

    print(f"\nSummary:")
    print(f"  Total time:        {total_time:.4f} secs")
    print(f"  Total requests:    {total_done}")
    print(f"  Slowest:           {durations[-1]:.4f} secs" if durations else "  Slowest: N/A")
    print(f"  Fastest:           {durations[0]:.4f} secs" if durations else "  Fastest: N/A")
    print(f"  Average:           {sum(durations) / len(durations):.4f} secs" if durations else "  Average: N/A")
    print(f"  Requests/sec:      {rps:.2f}")
    print(f"  Concurrency:       {concurrency}")

    if durations:
        def get_pct(p: float) -> float:
            idx = int(len(durations) * (p / 100.0))
            return durations[min(idx, len(durations) - 1)]

        print(f"\nLatency distribution:")
        print(f"  10% in {get_pct(10):.4f} secs")
        print(f"  25% in {get_pct(25):.4f} secs")
        print(f"  50% in {get_pct(50):.4f} secs")
        print(f"  75% in {get_pct(75):.4f} secs")
        print(f"  90% in {get_pct(90):.4f} secs")
        print(f"  95% in {get_pct(95):.4f} secs")
        print(f"  99% in {get_pct(99):.4f} secs")

    print(f"\nStatus code distribution:")
    for code, count in sorted(status_codes.items()):
        label = f"HTTP {code}" if code > 0 else "Connection Errors"
        print(f"  [{label}] {count} responses")

    if errors:
        error_counts = Counter(errors)
        print(f"\nError details:")
        for err, count in error_counts.most_common(5):
            print(f"  [{count}x] {err}")

def main():
    parser = argparse.ArgumentParser(description="Hey-compatible HTTP traffic generator & benchmark")
    parser.add_argument("url", help="Target URL (e.g. http://localhost:8080/)")
    parser.add_argument("-n", "--requests", type=int, default=200, help="Number of requests to run (default: 200)")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Number of workers to run concurrently (default: 10)")
    parser.add_argument("-m", "--method", type=str, default="GET", help="HTTP method (default: GET)")
    parser.add_argument("-z", "--duration", type=str, default=None, help="Duration for benchmark (e.g. 30s, 1m). Overrides -n")

    args = parser.parse_args()
    dur_secs = parse_duration(args.duration) if args.duration else None

    asyncio.run(run_benchmark(
        url=args.url,
        method=args.method.upper(),
        num_requests=args.requests,
        concurrency=args.concurrency,
        duration_seconds=dur_secs,
    ))

if __name__ == "__main__":
    main()
