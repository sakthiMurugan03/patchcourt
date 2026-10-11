"""Benchmark harness tests (Enhancement 6)."""
from patchcourt.benchmark import builtin_cases, latest_benchmark, run_benchmark
from patchcourt.benchmark.metrics import classify_failure, compute_metrics
from patchcourt.benchmark.store import save_benchmark


def test_builtin_cases_have_labels():
    cases = builtin_cases()
    assert len(cases) >= 8
    for c in cases:
        assert c.finding.file
        assert c.expected_status in {"SUPPORTED", "CONTRADICTED", "UNCERTAIN", "OUT_OF_SCOPE"}


def test_benchmark_is_fully_correct_on_builtin_set():
    result = run_benchmark()
    metrics = result["metrics"]
    assert metrics["status_accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["incorrect_dismissals"] == 0
    assert metrics["failures"] == 0
    for case in result["cases"]:
        assert case["failure"] is None
        assert case["status_correct"]


def test_visibility_case_hits_repository_policy():
    result = run_benchmark(cases=[c for c in builtin_cases() if c.id == "visibility-widening-vs-policy"])
    case = result["cases"][0]
    assert case["predicted_status"] == "CONTRADICTED"
    ids = {p["id"] for p in case["matched_policies"]}
    assert any("boundar" in i for i in ids)


def test_classify_failure_mapping():
    assert classify_failure("SUPPORTED", "SUPPORTED", True) is None
    assert classify_failure("SUPPORTED", "SUPPORTED", False) == "accepted_false_positive"
    assert classify_failure("CONTRADICTED", "CONTRADICTED", True) == "incorrectly_dismissed"
    assert classify_failure("UNCERTAIN", "SUPPORTED", True) == "status_mismatch"


def test_compute_metrics_math():
    results = [
        {"predicted_status": "SUPPORTED", "expected_status": "SUPPORTED", "predicted_actionable": True, "defect": True, "failure": None},
        {"predicted_status": "SUPPORTED", "expected_status": "SUPPORTED", "predicted_actionable": True, "defect": True, "failure": None},
        {"predicted_status": "SUPPORTED", "expected_status": "CONTRADICTED", "predicted_actionable": True, "defect": False, "failure": "accepted_false_positive"},
        {"predicted_status": "CONTRADICTED", "expected_status": "CONTRADICTED", "predicted_actionable": False, "defect": False, "failure": None},
        {"predicted_status": "UNCERTAIN", "expected_status": "SUPPORTED", "predicted_actionable": False, "defect": True, "failure": "incorrectly_dismissed"},
    ]
    metrics = compute_metrics(results)
    assert metrics["status_accuracy"] == 3 / 5
    assert abs(metrics["precision"] - (2/3)) < 1e-4  # 2 tp / (2 tp + 1 fp)
    assert abs(metrics["recall"] - (2/3)) < 1e-4
    assert metrics["incorrect_dismissals"] == 1
    assert metrics["confusion_matrix"] == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}


def test_save_and_load_latest(tmp_path, monkeypatch):
    from patchcourt.benchmark import store as store_module

    monkeypatch.setattr(store_module, "_reports_dir", lambda: tmp_path)
    result = {"generated_at": "x", "cases": []}
    save_benchmark(result)
    assert latest_benchmark() == result
    assert latest_benchmark()["cases"] == []