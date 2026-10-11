"""Finding-validator tests (Enhancement 1 + 2 + 3)."""
from patchcourt.adjudication.correlate import correlate_findings
from patchcourt.adjudication.rules import load_repository_policies
from patchcourt.adjudication.validator import (
    FindingValidator,
    added_line_numbers,
    validate_findings,
)
from patchcourt.tools.base import Finding


def f(tool="semgrep", file="app.py", line=2, sev=5, msg="boom", rule="R", rec="", cat=""):
    return Finding(tool=tool, file=file, line=line, message=msg, severity=sev, rule=rule, recommendation=rec, category=cat)


FILES = {
    "app.py": 'def lookup(user_id):\n    sql = "SELECT * FROM users WHERE id = " + user_id\n    return sql\n'
}


def test_real_sql_concat_is_supported():
    a = validate_findings(
        [f(tool="semgrep", line=2, msg="SQL injection risk", rule="python.lang.security.audit.sql-injection")],
        file_contents=FILES,
    )[0]
    assert a.status == "SUPPORTED"
    assert a.category == "security"


def test_parameterized_query_contradicts_sql_finding():
    files = {"app.py": 'def lookup(user_id):\n    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n'}
    a = validate_findings(
        [f(tool="sonarqube", line=2, msg="Potential SQL injection", rule="security:SQLInjection")],
        file_contents=files,
    )[0]
    assert a.status == "CONTRADICTED"
    assert "parameterized" in a.rationale or "safe pattern" in a.rationale


def test_visibility_widening_conflicts_with_api_policy():
    files = {
        "PaymentService.java": (
            "public class PaymentService {\n"
            "    private double calculateTax(double amount) {\n"
            "        return amount * 0.18;\n"
            "    }\n}\n"
        )
    }
    policy = load_repository_policies(
        extra_files={
            ".patchcourt/policies/api-boundaries.md": (
                "# API Boundaries\n\nInternal helper methods must remain private. Widening "
                "visibility is only justified when an external caller requires access.\n"
            )
        }
    )
    a = FindingValidator(policies=policy).validate(
        [
            f(
                tool="sonarqube",
                file="PaymentService.java",
                line=2,
                sev=3,
                msg="Method visibility could be increased to public",
                rule="squid:Visibility",
                rec="make calculateTax public",
            )
        ],
        file_contents=files,
    )[0]
    assert a.status == "CONTRADICTED"
    assert any("boundar" in p.id or "boundar" in p.title.lower() for p in a.policies)


def test_real_secret_supported():
    files = {"app.py": 'API_TOKEN = "sk-live-6fa3c0d9a1b2"\n'}
    a = validate_findings(
        [f(tool="gitleaks", line=1, msg="Hardcoded API key", rule="gitleaks:generic-api-key")],
        file_contents=files,
    )[0]
    assert a.status == "SUPPORTED"


def test_placeholder_secret_contradicted():
    files = {"app.py": 'API_KEY = "changeme"\n'}
    a = validate_findings(
        [f(tool="gitleaks", line=1, sev=3, msg="Hardcoded credential", rule="gitleaks:generic-api-key")],
        file_contents=files,
    )[0]
    assert a.status == "CONTRADICTED"


def test_out_of_scope_file():
    a = validate_findings(
        [f(tool="sonarqube", file="legacy.py", line=10, msg="smell", rule="py:S9999")],
        file_contents=FILES,
    )[0]
    assert a.status == "OUT_OF_SCOPE"


def test_uncorroborated_unknown_rule_is_uncertain():
    a = validate_findings(
        [f(tool="toolx", line=2, msg="esoteric rule", rule="unk:Z1")],
        file_contents=FILES,
    )[0]
    assert a.status == "UNCERTAIN"


def test_two_tools_agree_supports_uncatalogued_rule():
    findings = [
        f(tool="alpha", line=2, msg="esoteric rule", rule="unk:Z1"),
        f(tool="beta", line=2, msg="esoteric rule", rule="unk:Z1"),
    ]
    a = validate_findings(
        findings,
        file_contents=FILES,
        correlations=correlate_findings(findings),
    )[0]
    assert a.status == "SUPPORTED"
    assert a.corroborated
    assert a.corroborating_tools == ["beta"]


def test_supported_secret_carries_policy_evidence():
    files = {"app.py": 'API_KEY = "my_vault_secret"\n'}
    a = validate_findings(
        [f(tool="trufflehog", line=1, sev=5, msg="Hardcoded secret", rule="generic:secret")],
        file_contents=files,
    )[0]
    assert a.status == "SUPPORTED"
    assert any(e.tier == 3 for e in a.evidence)


def test_added_line_numbers_parses_hunks():
    patch = "diff --git a/app.py b/app.py\n@@ -0,0 +1,2 @@\n+line one\n+line two\n context\n+line three\n"
    assert added_line_numbers(patch) == {1, 2, 4}


def test_added_line_numbers_simplified_patch():
    patch = "+a\n+b\n c\n+d\n"
    assert added_line_numbers(patch) == {1, 2, 4}