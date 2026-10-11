"""Benchmark harness — labeled adjudication dataset + metrics (Enhancement 6)."""
from patchcourt.benchmark.cases import BenchmarkCase, FindingSpec, builtin_cases
from patchcourt.benchmark.metrics import compute_metrics
from patchcourt.benchmark.runner import run_benchmark
from patchcourt.benchmark.store import latest_benchmark, save_benchmark

__all__ = [
    "BenchmarkCase",
    "FindingSpec",
    "builtin_cases",
    "compute_metrics",
    "run_benchmark",
    "latest_benchmark",
    "save_benchmark",
]