"""Repository-aware rule catalogue and policy retrieval tests (Enhancement 2)."""
from patchcourt.adjudication.rules import (
    RULE_CATALOG,
    category_for,
    load_repository_policies,
    match_policies,
    rule_for,
)
from patchcourt.tools.base import Finding


def test_rule_for_bandit_alias():
    rule = rule_for(Finding(tool="bandit", file="a.py", line=1, message="", rule="B602"))
    assert rule is not None
    assert rule.id == "SHELL_TRUE"
    assert rule.category == "security"


def test_rule_for_message_keywords():
    rule = rule_for(Finding(tool="sonarqube", file="a.py", line=1, message="SQL injection risk", rule="security:SQLInjection"))
    assert rule is not None
    assert rule.id == "SQL_CONCAT"


def test_rule_for_unknown_returns_none():
    rule = rule_for(Finding(tool="x", file="a.py", line=1, message="que pasa", rule="unk:rule"))
    assert rule is None


def test_category_for_prefers_finding_category():
    f = Finding(tool="t", file="a.py", line=1, message="x", category="correctness")
    assert category_for(f, rule_for(f)) == "correctness"


def test_bundled_policies_loaded():
    policies = load_repository_policies()
    ids = {p.id for p in policies}
    assert "api-boundaries" in ids
    assert "security-policy" in ids


def test_repository_provided_policy_loaded():
    extra = {
        ".patchcourt/policies/my-rules.md": "# My Rules\n\nNever widen visibility in this repo.\n"
    }
    policies = load_repository_policies(extra_files=extra)
    ids = {p.id for p in policies}
    assert "repo:my-rules" in ids
    assert any(p.source == "repository" for p in policies)


def test_unrelated_files_not_treated_as_policies():
    policies = load_repository_policies(extra_files={"README.md": "not a policy"})
    assert not any(p.source == "repository" for p in policies)


def test_match_policies_visibility_text():
    policies = load_repository_policies()
    refs = match_policies("Method visibility could be increased to public", policies)
    assert any("boundar" in r.id or "boundar" in r.title.lower() for r in refs)


def test_rule_catalog_has_visibility_rule():
    assert RULE_CATALOG["VISIBILITY"].category == "maintainability"