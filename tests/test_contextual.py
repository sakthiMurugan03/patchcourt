"""Contextual severity/priority tests (Enhancement 4)."""
from patchcourt.adjudication.contextual import (
    assess_context,
    is_reachable,
    is_security_sensitive,
    summarize,
)
from patchcourt.agents.schemas import FindingAssessment


def test_security_reachable_sensitive_sev5_blocks():
    priority, action = assess_context(
        status="SUPPORTED",
        category="security",
        severity=5,
        file="app.py",
        line_text="subprocess.run(cmd, shell=True)",
        safeguard=False,
        pr_touched=True,
    )
    assert (priority, action) == ("critical", "block")


def test_security_with_safeguard_downgraded_to_review():
    priority, action = assess_context(
        status="SUPPORTED",
        category="security",
        severity=5,
        file="app.py",
        line_text="cur.execute('SELECT * FROM t WHERE id=?', (x,))",
        safeguard=True,
        pr_touched=True,
    )
    assert (priority, action) == ("medium", "review")


def test_security_comment_only_is_low():
    priority, action = assess_context(
        status="SUPPORTED",
        category="security",
        severity=5,
        file="app.py",
        line_text="# TODO: fix this",
        safeguard=False,
        pr_touched=True,
    )
    assert (priority, action) == ("low", "review")


def test_contradicted_is_info_acknowledge():
    assert assess_context(
        status="CONTRADICTED", category="security", severity=5, file="app.py",
        line_text="x", safeguard=False, pr_touched=True,
    ) == ("info", "acknowledge")


def test_uncertain_is_low_human_review():
    assert assess_context(
        status="UNCERTAIN", category="unknown", severity=3, file="app.py",
        line_text="x", safeguard=False, pr_touched=True,
    ) == ("low", "human_review")


def test_out_of_scope_is_info():
    assert assess_context(
        status="OUT_OF_SCOPE", category="unknown", severity=3, file="legacy.py",
        line_text="", safeguard=False, pr_touched=True,
    ) == ("info", "acknowledge")


def test_maintainability_high_when_severe_reachable_touched():
    priority, action = assess_context(
        status="SUPPORTED", category="maintainability", severity=4, file="billing.py",
        line_text="def process():", safeguard=False, pr_touched=True,
    )
    assert (priority, action) == ("high", "remediate")


def test_is_reachable_ignores_comments_and_blanks():
    assert is_reachable("x = 1")
    assert not is_reachable("")
    assert not is_reachable("# comment")
    assert not is_reachable("// comment")
    assert not is_reachable("/* block")
    assert is_reachable("+x = 1")


def test_is_security_sensitive_by_category_and_filename():
    assert is_security_sensitive("security", "whatever.py")
    assert is_security_sensitive("maintainability", "auth/login.py")
    assert not is_security_sensitive("maintainability", "app.py")


def test_summarize_counts():
    a1 = FindingAssessment(status="SUPPORTED", contextual_priority="critical", contextual_action="block")
    a2 = FindingAssessment(status="CONTRADICTED", contextual_priority="info", contextual_action="acknowledge")
    summary = summarize([a1, a2])
    assert summary["total"] == 2
    assert summary["blocking"] == 1
    assert summary["by_status"] == {"SUPPORTED": 1, "CONTRADICTED": 1}
    assert summary["by_action"]["acknowledge"] == 1