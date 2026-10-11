"""Offline demo workspace for the SonarQube-vs-PatchCourt comparison (Review 2).

Reuses the *real* patchcourt code paths — ``correlate_findings``,
``FindingValidator`` with the bundled repository policies, and the
deterministic judge — so the comparison you see in the dashboard is exactly
what the pipeline would produce, without needing a live SonarQube or Docker.

Four demonstration cases are exercised:

1. **Justified finding** — app.py:8 SQL built by string concatenation. Sonar
   flags it (python:S2077); PatchCourt reproduces the unsafe pattern and marks
   it SUPPORTED.
2. **Contextual verification** — PaymentService.java:2. Sonar suggests removing
   an "unused" private method (java:S1144); the repository api-boundaries policy
   says internal helpers stay private, so PatchCourt marks the implied change
   CONTRADICTED and cites the policy.
3. **Two-tool corroboration / disagreement** — app.py:8 is also flagged by
   Bandit (B608) from a second tool, so PatchCourt shows the agreement and the
   corroborating tools. Severity is preserved; corroboration is never
   conflated with certainty.
4. **Agents disagree → evidence-backed debate + deterministic judge** — Security
   vs Pragmatist debate the shell=True call; the judge returns BLOCK driven by
   T1 tool evidence, never by the T5-only claims.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from patchcourt.adjudication.correlate import correlate_findings
from patchcourt.adjudication.rules import load_repository_policies
from patchcourt.adjudication.validator import FindingValidator
from patchcourt.agents.schemas import Claim, Evidence, PRContext
from patchcourt.baseline.sonarqube_baseline import compare_findings, compare_with_review
from patchcourt.judge.scoring import build_report
from patchcourt.tools.base import Finding

DEMO_PR_URL = "https://github.com/patchcourt/demo/pull/1337"

_FILES: dict[str, str] = {
    "app.py": (
        "import subprocess\n"
        "import os\n"
        "\n"
        "def deploy(command):\n"
        "    subprocess.call(command, shell=True)\n"
        "\n"
        "def lookup(user_id):\n"
        "    sql = \"SELECT * FROM users WHERE id = \" + user_id\n"
        "    return sql\n"
        "\n"
        "API_TOKEN = \"sk-live-6fa3c0d9a1b2\"\n"
    ),
    "billing.py": (
        "import sqlite3\n"
        "\n"
        "def lookup(user_id):\n"
        "    conn = sqlite3.connect(\"app.db\")\n"
        "    cur = conn.cursor()\n"
        "    cur.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))\n"
        "    return cur.fetchone()\n"
    ),
    "PaymentService.java": (
        "public class PaymentService {\n"
        "    private double calculateTax(double amount) {\n"
        "        return amount * 0.18;\n"
        "    }\n"
        "}\n"
    ),
}

_PATCHES: dict[str, str] = {
    fname: "\n".join(f"+{line}" if line.strip() else line for line in content.splitlines())
    for fname, content in _FILES.items()
}


def demo_comparison_pr() -> PRContext:
    return PRContext(
        owner="patchcourt",
        repo="demo",
        pr_number=1337,
        title="Demo: deployment, payment lookup and billing endpoints",
        body=(
            "Comparison demo PR used by the Comparative Review workspace. "
            "Contains justified findings, a policy-contested Java change, a "
            "cross-tool corroboration, and a Security-vs-Pragmatist debate."
        ),
        diff="\n".join(f"diff --git a/{k} b/{k}\n" + v for k, v in _PATCHES.items()),
        file_contents=_FILES,
        patches=_PATCHES,
        changed_files=[{"filename": k, "patch": v} for k, v in _PATCHES.items()],
        rag_query="Demo: deployment, payment lookup and billing endpoints",
    )


def demo_baseline(pr_url: str = DEMO_PR_URL) -> dict:
    """A SonarQube-shaped baseline report for the demo PR.

    Every issue is direct static-analysis evidence (provenance_tier = 1);
    severity is SonarQube's own judgement and is preserved verbatim.
    """
    issues = [
        {
            "issue_key": "APP-SHELL-1",
            "file": "app.py",
            "line": 5,
            "severity": "CRITICAL",
            "status": "OPEN",
            "type": "VULNERABILITY",
            "rule": "python:S6042",
            "message": "Change this code to not construct the command from user-controlled data.",
            "in_pr": True,
            "provenance": "static-analysis",
            "provenance_tier": 1,
        },
        {
            "issue_key": "APP-SQL-2",
            "file": "app.py",
            "line": 8,
            "severity": "CRITICAL",
            "status": "OPEN",
            "type": "VULNERABILITY",
            "rule": "python:S2077",
            "message": "Formatting SQL queries is security-sensitive.",
            "in_pr": True,
            "provenance": "static-analysis",
            "provenance_tier": 1,
        },
        {
            "issue_key": "APP-SECRET-3",
            "file": "app.py",
            "line": 11,
            "severity": "MAJOR",
            "status": "OPEN",
            "type": "VULNERABILITY",
            "rule": "python:S2068",
            "message": "Hard-coded credentials are security-sensitive.",
            "in_pr": True,
            "provenance": "static-analysis",
            "provenance_tier": 1,
        },
        {
            "issue_key": "BILLING-SQL-4",
            "file": "billing.py",
            "line": 6,
            "severity": "CRITICAL",
            "status": "OPEN",
            "type": "VULNERABILITY",
            "rule": "python:S2077",
            "message": "Formatting SQL queries is security-sensitive.",
            "in_pr": True,
            "provenance": "static-analysis",
            "provenance_tier": 1,
        },
        {
            "issue_key": "PAY-S1144-5",
            "file": "PaymentService.java",
            "line": 2,
            "severity": "MINOR",
            "status": "OPEN",
            "type": "CODE_SMELL",
            "rule": "java:S1144",
            "message": "Remove this unused private 'calculateTax' method.",
            "in_pr": True,
            "provenance": "static-analysis",
            "provenance_tier": 1,
        },
    ]
    return {
        "generated_at": "2026-10-11T00:00:00+00:00",
        "pr_url": pr_url,
        "component": "pr-patchcourt-demo-1337",
        "server_url": "https://sonarqube.example.internal",
        "baseline_scope": {
            "included": "unresolved (open) issues for the component",
            "excluded": "resolved, closed, or false-positive-marked issues",
            "query": {"resolved": "false"},
            "note": (
                "Baseline reflects SonarQube's current open-issue set at scan time. "
                "Issues previously resolved or marked false-positive are out of scope "
                "and are not re-evaluated here."
            ),
        },
        "total_open_issues": len(issues),
        "issues_touching_pr": len(issues),
        "summary": {
            "vulnerabilities": 4,
            "bugs": 0,
            "code_smells": 1,
        },
        "issues": issues,
    }


def demo_findings() -> list[Finding]:
    """Raw findings from multiple tools, mirroring what the scanners emit for
    the demo files."""
    return [
        Finding(
            tool="sonarqube", file="app.py", line=5, severity=5,
            message="Change this code to not construct the command from user-controlled data.",
            rule="python:S6042", category="security",
        ),
        Finding(
            tool="semgrep", file="app.py", line=5, severity=4,
            message="subprocess with shell=True", rule="python.lang.security.audit.subprocess.shell-true",
            category="security",
        ),
        Finding(
            tool="sonarqube", file="app.py", line=8, severity=5,
            message="Formatting SQL queries is security-sensitive.",
            rule="python:S2077", category="security",
        ),
        Finding(
            tool="bandit", file="app.py", line=8, severity=3,
            message="Possible SQL injection vector through string-based query construction.",
            rule="B608", category="security",
        ),
        Finding(
            tool="sonarqube", file="app.py", line=11, severity=3,
            message="Hard-coded credentials are security-sensitive.",
            rule="python:S2068", category="security",
        ),
        Finding(
            tool="gitleaks", file="app.py", line=11, severity=5,
            message="Hardcoded API key detected", rule="gitleaks:generic-api-key",
            category="security",
        ),
        Finding(
            tool="sonarqube", file="billing.py", line=6, severity=5,
            message="Formatting SQL queries is security-sensitive.",
            rule="python:S2077", category="security",
        ),
        Finding(
            tool="sonarqube", file="PaymentService.java", line=2, severity=3,
            message="Remove this unused private 'calculateTax' method.",
            rule="java:S1144", category="maintainability",
            recommendation="make calculateTax public so it can be tested externally",
        ),
    ]


def _claim(
    agent: str,
    issue: str,
    file: str,
    line: int,
    severity: int,
    tiers: list[int],
    corroborated: bool = False,
    source: str = "tool",
) -> Claim:
    return Claim(
        agent=agent,
        issue=issue,
        file=file,
        line=line,
        severity=severity,
        evidence=[Evidence(tier=t, text=f"evidence tier T{t}") for t in tiers],
        confidence=1.0,
        tier=min(tiers),
        corroborated=corroborated,
        source=source,
    )


def demo_claims() -> list[Claim]:
    """Three-agent claim set with a deliberate Security-vs-Pragmatist dispute.

    BLOCK must come from the T1 tool findings, never from the T5-only claims.
    """
    return [
        _claim("security", "Command execution with shell=True", "app.py", 5, 5, [1], corroborated=True),
        _claim("security", "SQL built by string concatenation", "app.py", 8, 5, [1, 2], corroborated=True),
        _claim("security", "Hardcoded API credential", "app.py", 11, 4, [1], corroborated=True),
        _claim("quality", "Missing error handling around deploy", "app.py", 5, 3, [5], source="llm"),
        _claim("pragmatist", "Shell usage acceptable in internal deploy script", "app.py", 5, 2, [5], source="llm"),
        _claim(
            "quality",
            "calculateTax visibility follows repository api-boundaries",
            "PaymentService.java", 2, 2, [3], source="llm",
        ),
    ]


def demo_debate() -> list:
    """One bounded, evidence-backed debate (Security vs Pragmatist)."""
    return [
        SimpleNamespace(
            claim=SimpleNamespace(file="app.py", issue="Command execution with shell=True"),
            supporting=(
                "Static analysis (python:S6042 + semgrep shell-true) reproduced "
                "subprocess.call(command, shell=True) on app.py:5 with a mutable "
                "command argument. T1 evidence; unsafeness is reproducible, not opinion."
            ),
            opposing=(
                "Deploy script arguments come from a trusted config, so the shell "
                "interpreter is not exposed to attacker-controlled input in practice."
            ),
            rounds=2,
        )
    ]


def run_demo_comparison(pr_url: str = DEMO_PR_URL) -> dict:
    """Adjudicate the demo findings and produce the comparison workspace payload."""
    findings = demo_findings()
    correlations = correlate_findings(findings)
    policies = load_repository_policies()
    assessments = FindingValidator(policies=policies).validate(
        findings,
        file_contents=_FILES,
        correlations=correlations,
        patches=_PATCHES,
    )

    claims = demo_claims()
    report = build_report(
        pr_url,
        claims,
        demo_debate(),
        assessments=assessments,
        correlations=correlations,
    )

    baseline = demo_baseline(pr_url)
    finding_comparison = compare_findings(
        baseline,
        report.finding_assessments,
        report.verdict,
        report.overall_score,
    )
    legacy = compare_with_review(
        baseline, [c.model_dump() for c in report.claims], report.verdict, report.overall_score
    )
    baseline["patchcourt"] = {
        "verdict": report.verdict,
        "overall_score": report.overall_score,
        "comparison": legacy,
        "finding_comparison": finding_comparison,
        "contextual_summary": report.contextual_summary,
        "assessment_count": len(report.finding_assessments),
    }

    payload: dict[str, Any] = json.loads(json.dumps({"baseline": baseline, "report": report.model_dump()}))

    # Diagnose which of the four demo scenarios each baseline issue exercises.
    scenario_map = {
        ("app.py", 5): "demo-1-justified + demo-4-disagreement",
        ("app.py", 8): "demo-1-justified + demo-3-corroboration",
        ("app.py", 11): "demo-1-justified",
        ("billing.py", 6): "demo-2-contextual",
        ("PaymentService.java", 2): "demo-2-contextual",
    }
    for row in payload["baseline"].get("patchcourt", {}).get("finding_comparison", {}).get("findings", []):
        row["scenario"] = scenario_map.get((row["sonar"]["file"], row["sonar"]["line"]), "")
    return payload