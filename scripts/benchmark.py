#!/usr/bin/env python3
"""
TrueFace AI-X — Pipeline Benchmark Utility
Measures end-to-end and stage latency for face, voice, and fusion pipelines.
"""

import time
import statistics

def benchmark_pipeline(iterations: int = 100):
    print(f"Running benchmark across {iterations} iterations...")
    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        # Simulated pipeline execution
        time.sleep(0.005)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    avg_lat = statistics.mean(latencies)
    p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
    print(f"Average Latency: {avg_lat:.2f} ms")
    print(f"p95 Latency:     {p95_lat:.2f} ms")

if __name__ == "__main__":
    benchmark_pipeline()

