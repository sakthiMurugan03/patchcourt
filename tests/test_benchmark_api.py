"""Benchmark API tests (Enhancement 6)."""
from fastapi.testclient import TestClient

from patchcourt.api.app import app

client = TestClient(app)


def test_benchmark_run_creates_report():
    resp = client.post("/api/benchmark/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metrics"]["total_cases"] == 8
    assert body["metrics"]["status_accuracy"] == 1.0


def test_benchmark_latest_returns_last():
    client.post("/api/benchmark/run")  # ensure exists
    resp = client.get("/api/benchmark/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metrics"]["status_accuracy"] == 1.0


def test_benchmark_latest_404_when_missing(tmp_path, monkeypatch):
    from patchcourt.benchmark import store as store_module
    from patchcourt.api import app as app_module

    monkeypatch.setattr(store_module, "_reports_dir", lambda: tmp_path / "reports" / "nonexist")
    # Get a fresh client for this isolation? Or just call; easier to stub latest_benchmark
    from patchcourt import benchmark as bm

    monkeypatch.setattr(bm, "latest_benchmark", lambda: None)
    resp = client.get("/api/benchmark/latest")
    assert resp.status_code == 404
    body = resp.json()
    detail = body.get("detail") or body
    assert detail["category"] == "not_found"