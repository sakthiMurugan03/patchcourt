"""Labeled benchmark cases for testing PatchCourt's finding adjudication.

Each case is one scanner finding plus independent ground truth. The statuses
are PatchCourt-internal; the defect flag is the independently verified truth.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FindingSpec(BaseModel):
    tool: str
    file: str
    line: int = 0
    message: str = ""
    severity: int = 3
    rule: str = ""
    category: str = ""
    recommendation: str = ""


class BenchmarkCase(BaseModel):
    id: str
    title: str
    description: str = ""
    files: dict[str, str] = Field(default_factory=dict)
    patches: dict[str, str] = Field(default_factory=dict)
    finding: FindingSpec
    expected_status: str
    ground_truth_defect: bool
    repo_policies: dict[str, str] = Field(default_factory=dict)


BUILTIN_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        id="sql-concat-real",
        title="SQL string concatenation",
        description="A value is concatenated into a SELECT — independently confirmed.",
        files={"app.py": 'def lookup(user_id):\n    sql = "SELECT * FROM users WHERE id = " + user_id\n    return sql\n'},
        patches={"app.py": "diff --git a/app.py b/app.py\n@@ -0,0 +1 @@\n+def lookup(user_id):\n+    sql = \"SELECT * FROM users WHERE id = \" + user_id\n+    return sql\n"},
        finding=FindingSpec(
            tool="semgrep",
            file="app.py",
            line=2,
            message="Potential SQL injection; concatenation of values into a query.",
            severity=5,
            rule="python.lang.security.audit.sql-injection",
            category="security",
        ),
        expected_status="SUPPORTED",
        ground_truth_defect=True,
    ),
    BenchmarkCase(
        id="sql-parameterized-fp",
        title="SQL finding on a parameterized query",
        description="Scanner flags SQL but the query is parameterized — likely false positive.",
        files={"app.py": 'def lookup(user_id):\n    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n'},
        patches={"app.py": "diff --git a/app.py b/app.py\n@@ -0,0 +1 @@\n+def lookup(user_id):\n+    cur.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))\n"},
        finding=FindingSpec(
            tool="sonarqube",
            file="app.py",
            line=2,
            message="Potential SQL injection.",
            severity=5,
            rule="security:SQLInjection",
            category="security",
        ),
        expected_status="CONTRADICTED",
        ground_truth_defect=False,
    ),
    BenchmarkCase(
        id="visibility-widening-vs-policy",
        title="Visibility widening conflicts with API-boundary policy",
        description="Tool recommends making a private helper public; the repository policy forbids it.",
        files={"PaymentService.java": "public class PaymentService {\n    private double calculateTax(double amount) {\n        return amount * 0.18;\n    }\n}\n"},
        patches={"PaymentService.java": "diff --git a/PaymentService.java b/PaymentService.java\n@@ -0,0 +1 @@\n+public class PaymentService {\n+    private double calculateTax(double amount) {\n+        return amount * 0.18;\n+    }\n+}\n"},
        finding=FindingSpec(
            tool="sonarqube",
            file="PaymentService.java",
            line=2,
            message="Method visibility could be increased to public.",
            severity=3,
            rule="squid:Visibility",
            category="maintainability",
            recommendation="make calculateTax public",
        ),
        repo_policies={
            ".patchcourt/policies/api-boundaries.md": (
                "# API Boundaries\n\nInternal helper methods must remain private. Widening "
                "visibility is only justified when an external caller requires access.\n"
            )
        },
        expected_status="CONTRADICTED",
        ground_truth_defect=False,
    ),
    BenchmarkCase(
        id="shell-true-real",
        title="Shell invocation with untrusted command",
        description="subprocess shell=True executes through a shell — confirmed.",
        files={"app.py": "import subprocess\n\nsubprocess.call(cmd, shell=True)\n"},
        patches={"app.py": "diff --git a/app.py b/app.py\n@@ -0,0 +1 @@\n+subprocess.call(cmd, shell=True)\n"},
        finding=FindingSpec(
            tool="bandit",
            file="app.py",
            line=3,
            message="subprocess call with shell=True is dangerous.",
            severity=5,
            rule="B602",
            category="security",
        ),
        expected_status="SUPPORTED",
        ground_truth_defect=True,
    ),
    BenchmarkCase(
        id="hardcoded-secret-real",
        title="Real hardcoded API token",
        description="A live-looking token is committed to source — confirmed.",
        files={"app.py": 'API_TOKEN = "sk-live-6fa3c0d9a1b2"\n'},
        patches={"app.py": "diff --git a/app.py b/app.py\n@@ -0,0 +1 @@\n+API_TOKEN = \"sk-live-6fa3c0d9a1b2\"\n"},
        finding=FindingSpec(
            tool="gitleaks",
            file="app.py",
            line=1,
            message="Hardcoded API key detected.",
            severity=5,
            rule="gitleaks:generic-api-key",
            category="security",
        ),
        expected_status="SUPPORTED",
        ground_truth_defect=True,
    ),
    BenchmarkCase(
        id="hardcoded-secret-placeholder",
        title="Placeholder secret value",
        description="The 'secret' is a changeme placeholder, not a real credential.",
        files={"app.py": 'API_KEY = "changeme"\n'},
        patches={"app.py": "diff --git a/app.py b/app.py\n@@ -0,0 +1 @@\n+API_KEY = \"changeme\"\n"},
        finding=FindingSpec(
            tool="gitleaks",
            file="app.py",
            line=1,
            message="Hardcoded credential detected.",
            severity=3,
            rule="gitleaks:generic-api-key",
            category="security",
        ),
        expected_status="CONTRADICTED",
        ground_truth_defect=False,
    ),
    BenchmarkCase(
        id="out-of-scope-file",
        title="Finding outside the change",
        description="The flagged file is not part of the reviewed change.",
        files={"app.py": "print(1)\n"},
        finding=FindingSpec(
            tool="sonarqube",
            file="legacy.py",
            line=10,
            message="Legacy code smell.",
            severity=3,
            rule="py:S9999",
            category="maintainability",
        ),
        expected_status="OUT_OF_SCOPE",
        ground_truth_defect=False,
    ),
    BenchmarkCase(
        id="unused-variable-smell",
        title="Unused declaration code smell",
        description="A maintainability smell that is not a runtime defect.",
        files={"app.py": "import os\n\nx = 1\n"},
        finding=FindingSpec(
            tool="sonarqube",
            file="app.py",
            line=3,
            message="Local variable 'x' is unused.",
            severity=2,
            rule="py:S1481",
            category="maintainability",
        ),
        expected_status="UNCERTAIN",
        ground_truth_defect=False,
    ),
]


def builtin_cases() -> list[BenchmarkCase]:
    return [case.model_copy(deep=True) for case in BUILTIN_CASES]