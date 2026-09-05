"""Small HTTP concurrency smoke test for a deployed GBM Gene Analysis host.

This is intentionally not a scale/load benchmark. It checks that a small number
of simultaneous researcher sessions can reach the deployed app without obvious
HTTP failures or pathological latency.

Example:
    python scripts/host_smoke.py https://example.streamlit.app --requests 12 --concurrency 3
"""
from __future__ import annotations

import argparse
import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request


def fetch(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "gbm-gene-analysis-release-smoke/7.0.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(4096)
            status = int(response.status)
        error = None
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        error = str(exc)
    except Exception as exc:  # network/host boundary
        status = None
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started
    return {"status": status, "latency_seconds": elapsed, "error": error}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("--requests and --concurrency must be positive")
    concurrency = min(args.concurrency, args.requests)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: fetch(args.url, args.timeout), range(args.requests)))

    latencies = [row["latency_seconds"] for row in results]
    successes = [row for row in results if row["status"] is not None and 200 <= row["status"] < 400]
    failures = [row for row in results if row not in successes]
    ordered = sorted(latencies)
    p95_index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))

    print(f"url={args.url}")
    print(f"requests={args.requests} concurrency={concurrency}")
    print(f"successes={len(successes)} failures={len(failures)}")
    print(f"median_seconds={statistics.median(latencies):.3f}")
    print(f"p95_seconds={ordered[p95_index]:.3f}")
    if failures:
        for row in failures[:5]:
            print(f"failure status={row['status']} latency={row['latency_seconds']:.3f}s error={row['error']}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
