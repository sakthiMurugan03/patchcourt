"""Tests for the dynamic SonarQube-vs-PatchCourt comparison derived from a review."""
import importlib

from fastapi.testclient import TestClient

from patchcourt.agents.schemas import (
    Claim,
    Evidence,
    FindingAssessment,
    ReviewReport,
)
from patchcourt.comparison import build_baseline_from_review, build_review_comparison


def _fake_report() -> ReviewReport:
    return ReviewReport(
        pr_url="https://github.com/acme/web/pull/7",
        overall_score=8.0,
        verdict="BLOCK",
        claims=[
            Claim(
                agent="tools",
                issue="SQL built by string concatenation",
                file="app.py",
                line=5,
                severity=5,
                evidence=[Evidence(tier=1, text="[sonarqube] python:S2077")],
                confidence=1.0,
                tier=1,
                corroborated=True,
                source="tool",
            ),
            Claim(
                agent="quality",
                issue="unused private method",
                file="Service.java",
                line=2,
                severity=2,
                evidence=[Evidence(tier=5, text="llm guess")],
                confidence=0.3,
                tier=5,
                source="llm",
            ),
        ],
        finding_assessments=[
            FindingAssessment(
                tool="sonarqube",
                file="app.py",
                line=5,
                rule="python:S2077",
                message="Formatting SQL queries is security-sensitive.",
                severity=5,
                category="security",
                status="SUPPORTED",
                rationale="unsafe pattern reproduced",
                corroborated=True,
                corroborating_tools=["bandit"],
                contextual_priority="BLOCK",
                contextual_action="Fix before merge",
            ),
            FindingAssessment(
                tool="sonarqube",
                file="Service.java",
                line=2,
                rule="java:S1144",
                message="Remove this unused private method.",
                severity=3,
                category="maintainability",
                status="CONTRADICTED",
                rationale="policy keeps helpers private",
                contextual_priority="MONITOR",
            ),
        ],
        debate_transcripts=[],
    )


def test_build_baseline_from_review_shapes_issues():
    baseline = build_baseline_from_review(_fake_report())

    assert baseline["pr_url"] == "https://github.com/acme/web/pull/7"
    assert baseline["total_open_issues"] == 2
    assert baseline["issues_touching_pr"] == 2
    assert baseline["component"] == "pr-acme-web-7"
    # severity ints are mapped to SonarQube's own labels, not tiers.
    by_file = {i["file"]: i for i in baseline["issues"]}
    assert by_file["app.py"]["severity"] == "BLOCKER"
    assert by_file["Service.java"]["severity"] == "MAJOR"
    assert by_file["app.py"]["type"] == "VULNERABILITY"
    assert by_file["Service.java"]["type"] == "CODE_SMELL"
    assert all(i["provenance_tier"] == 1 for i in baseline["issues"])
    assert baseline["summary"] == {"vulnerabilities": 1, "bugs": 0, "code_smells": 1}


def test_build_review_comparison_groups_by_adjudication():
    payload = build_review_comparison(_fake_report())
    pc = payload["patchcourt"]

    assert pc["verdict"] == "BLOCK"
    assert pc["overall_score"] == 8.0
    assert pc["assessment_count"] == 2

    fc = pc["finding_comparison"]
    assert fc["total_in_pr"] == 2
    assert fc["adjudicated"] == 2
    assert fc["coverage"] == 1.0
    assert fc["counts"]["confirmed"] == 1
    assert fc["counts"]["contradicted"] == 1
    assert fc["counts"]["unmatched"] == 0

    # legacy claim-based reconciliation: app.py backed, Service.java unbacked.
    legacy = pc["comparison"]
    assert legacy["counts"]["raw"] == 2
    assert legacy["counts"]["confirmed"] == 1
    assert legacy["counts"]["suppressed"] == 1


def test_build_review_comparison_empty_review():
    report = ReviewReport(pr_url="https://github.com/acme/web/pull/9")
    payload = build_review_comparison(report)

    assert payload["total_open_issues"] == 0
    assert payload["patchcourt"]["finding_comparison"]["counts"]["unmatched"] == 0
    assert payload["patchcourt"]["finding_comparison"]["coverage"] == 0.0


def test_review_endpoint_attaches_baseline_report(monkeypatch):
    async def _fake_review(_pr_url, **_kw):
        return _fake_report()

    _api_module = importlib.import_module("patchcourt.api.app")
    monkeypatch.setattr(_api_module, "run_review", _fake_review)

    from patchcourt.api.app import app

    with TestClient(app) as c:
        resp = c.post("/api/review", json={"pr_url": "https://github.com/acme/web/pull/7"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pr_url"] == "https://github.com/acme/web/pull/7"
        baseline = body["baseline_report"]
        assert baseline["total_open_issues"] == 2
        assert baseline["patchcourt"]["verdict"] == "BLOCK"
        assert baseline["patchcourt"]["finding_comparison"]["counts"]["confirmed"] == 1
