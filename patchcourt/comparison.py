"""Dynamic SonarQube-vs-PatchCourt comparison derived from a live review.

Unlike :mod:`patchcourt.demo_comparison` (a fixed, hand-authored workspace),
this module builds the comparison for *whatever* PR was just reviewed: the
static-analysis findings PatchCourt adjudicated are reshaped into a
SonarQube-shaped baseline, then reconciled against the very same review's
``FindingAssessment`` set via the shared helpers in
:mod:`patchcourt.baseline.sonarqube_baseline`.

The result is attached to ``ReviewReport.baseline_report`` by the review
endpoints, so every dashboard tab — including the Comparison tab — renders
from the single shared report and resets automatically on the next review.
This works fully offline: no SonarQube server or Docker scan is required.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from patchcourt.baseline.sonarqube_baseline import (
    PROVENANCE,
    PROVENANCE_TIER,
    compare_findings,
    compare_with_review,
    parse_pr_url,
    project_key_for_pr,
)

# Scanner severity labels are SonarQube's own vocabulary; PatchCourt's internal
# finding severity is a 1–5 integer. This is a presentation mapping only — it
# never feeds evidence tiers (findings stay T1 provenance regardless).
_SEVERITY_LABEL = {5: "BLOCKER", 4: "CRITICAL", 3: "MAJOR", 2: "MINOR", 1: "INFO"}

_TYPE_FOR_CATEGORY = {
    "security": "VULNERABILITY",
    "correctness": "BUG",
    "maintainability": "CODE_SMELL",
}


def _component_for(pr_url: str) -> str:
    try:
        owner, repo, num = parse_pr_url(pr_url)
        return project_key_for_pr(owner, repo, num)
    except ValueError:
        return "patchcourt-review"


def _assessment_to_issue(a: Any, index: int) -> dict:
    category = getattr(a, "category", "") or ""
    severity = int(getattr(a, "severity", 3) or 3)
    return {
        "issue_key": f"PC-{index + 1}",
        "file": getattr(a, "file", ""),
        "line": getattr(a, "line", 0),
        "severity": _SEVERITY_LABEL.get(severity, "MAJOR"),
        "status": "OPEN",
        "type": _TYPE_FOR_CATEGORY.get(category, "CODE_SMELL"),
        "rule": getattr(a, "rule", ""),
        "message": (getattr(a, "message", "") or "")[:300],
        "in_pr": True,
        # Scanner findings are direct static-analysis evidence → T1 provenance.
        "provenance": PROVENANCE,
        "provenance_tier": PROVENANCE_TIER,
    }


def build_baseline_from_review(report: Any) -> dict:
    """Reshape a review's tool-backed findings into a SonarQube-shaped baseline.

    Only findings that actually came from a static-analysis tool are included:
    LLM-only claims never masquerade as scanner output.
    """
    assessments = list(getattr(report, "finding_assessments", []) or [])
    tool_findings = [a for a in assessments if (getattr(a, "tool", "") or "") not in ("", "llm")]
    issues = [_assessment_to_issue(a, i) for i, a in enumerate(tool_findings)]

    pr_url = getattr(report, "pr_url", "")
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "pr_url": pr_url,
        "component": _component_for(pr_url),
        "server_url": "derived://local-review",
        "baseline_scope": {
            "included": "static-analysis findings adjudicated in this review",
            "excluded": "LLM-only claims (no scanner provenance)",
            "query": {},
            "note": (
                "Derived baseline: the review's own tool-backed findings, reshaped "
                "into SonarQube's issue shape so adjudication can be compared "
                "finding-by-finding. No live SonarQube server is queried."
            ),
        },
        "total_open_issues": len(issues),
        "issues_touching_pr": sum(1 for i in issues if i["in_pr"]),
        "summary": {
            "vulnerabilities": sum(1 for i in issues if i["type"] == "VULNERABILITY"),
            "bugs": sum(1 for i in issues if i["type"] == "BUG"),
            "code_smells": sum(1 for i in issues if i["type"] == "CODE_SMELL"),
        },
        "issues": issues,
    }


def build_review_comparison(report: Any) -> dict:
    """Full comparison payload for the active review (baseline + PatchCourt).

    Mirrors the shape produced by ``run_demo_comparison`` so the dashboard's
    Comparison tab can render either source unchanged. Attach the return value
    to ``ReviewReport.baseline_report``.
    """
    baseline = build_baseline_from_review(report)
    claims = [c.model_dump() if hasattr(c, "model_dump") else c for c in (getattr(report, "claims", []) or [])]
    verdict = getattr(report, "verdict", "")
    overall_score = float(getattr(report, "overall_score", 0.0) or 0.0)
    assessments = list(getattr(report, "finding_assessments", []) or [])

    baseline["patchcourt"] = {
        "verdict": verdict,
        "overall_score": overall_score,
        "comparison": compare_with_review(baseline, claims, verdict, overall_score),
        "finding_comparison": compare_findings(baseline, assessments, verdict, overall_score),
        "contextual_summary": getattr(report, "contextual_summary", {}) or {},
        "assessment_count": len(assessments),
    }
    return baseline
