"""Benchmark metrics — precision/recall/F1 over adjudicated findings."""
from __future__ import annotations

ACTIONABLE_STATUS = "SUPPORTED"
DISMISSED_STATUSES = ("CONTRADICTED", "OUT_OF_SCOPE")


def classify_failure(predicted: str, expected: str, defect: bool) -> str | None:
    """Classify a case-level failure against independent ground truth."""
    if predicted == ACTIONABLE_STATUS and not defect:
        return "accepted_false_positive"
    if predicted in DISMISSED_STATUSES and defect:
        return "incorrectly_dismissed"
    if predicted != expected:
        return "status_mismatch"
    return None


def compute_metrics(results: list[dict]) -> dict:
    """Metrics over per-case results. A case is 'actionable' when the validator
    marked the finding SUPPORTED; the ground-truth defect flag is the label."""
    total = len(results)
    correct = sum(1 for r in results if r["predicted_status"] == r["expected_status"])
    tp = sum(1 for r in results if r["predicted_actionable"] and r["defect"])
    fp = sum(1 for r in results if r["predicted_actionable"] and not r["defect"])
    fn = sum(1 for r in results if not r["predicted_actionable"] and r["defect"])
    tn = sum(1 for r in results if not r["predicted_actionable"] and not r["defect"])

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0.0
    incorrect_dismissals = sum(
        1 for r in results if r["failure"] == "incorrectly_dismissed"
    )

    return {
        "total_cases": total,
        "status_accuracy": correct / total if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "incorrect_dismissals": incorrect_dismissals,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "failures": sum(1 for r in results if r["failure"]),
    }