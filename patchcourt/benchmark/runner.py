"""Benchmark runner — adjudicate a labeled dataset and report metrics."""
from __future__ import annotations

import datetime as _dt

from patchcourt.adjudication import FindingValidator, correlate_findings, load_repository_policies
from patchcourt.benchmark.cases import BenchmarkCase, builtin_cases
from patchcourt.benchmark.metrics import classify_failure, compute_metrics
from patchcourt.tools.base import Finding


def _to_finding(case: BenchmarkCase) -> Finding:
    f = case.finding
    return Finding(
        tool=f.tool,
        file=f.file,
        line=int(f.line or 0),
        message=f.message,
        severity=int(f.severity or 3),
        rule=f.rule,
        category=f.category,
        recommendation=f.recommendation,
    )


def run_benchmark(cases: list[BenchmarkCase] | None = None) -> dict:
    """Adjudicate every case offline and return a metrics-bearing report."""
    cases = list(cases) if cases is not None else builtin_cases()
    results: list[dict] = []
    for case in cases:
        finding = _to_finding(case)
        policies = load_repository_policies(extra_files=case.repo_policies)
        correlations = correlate_findings([finding])
        assessments = FindingValidator(policies=policies).validate(
            [finding],
            file_contents=case.files,
            correlations=correlations,
            patches=case.patches or None,
        )
        assessment = assessments[0] if assessments else None
        predicted = assessment.status if assessment else "UNCERTAIN"
        failure = classify_failure(predicted, case.expected_status, case.ground_truth_defect)
        results.append(
            {
                "id": case.id,
                "title": case.title,
                "description": case.description,
                "expected_status": case.expected_status,
                "predicted_status": predicted,
                "status_correct": predicted == case.expected_status,
                "defect": case.ground_truth_defect,
                "predicted_actionable": predicted == "SUPPORTED",
                "failure": failure,
                "actionable_details": {
                    "priority": assessment.contextual_priority if assessment else "",
                    "action": assessment.contextual_action if assessment else "",
                },
                "rationale": assessment.rationale if assessment else "",
                "matched_policies": [
                    {"id": p.id, "title": p.title} for p in (assessment.policies if assessment else [])
                ],
            }
        )

    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "metrics": compute_metrics(results),
        "cases": results,
    }