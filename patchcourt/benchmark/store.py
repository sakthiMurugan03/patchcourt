"""Benchmark report persistence — save/read ``reports/benchmark-latest.json``."""
from __future__ import annotations

import json
from pathlib import Path


def _reports_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "reports"


def save_benchmark(result: dict) -> Path:
    out_dir = _reports_dir()
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "benchmark-latest.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path


def latest_benchmark() -> dict | None:
    path = _reports_dir() / "benchmark-latest.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)