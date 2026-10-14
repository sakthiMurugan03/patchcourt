"""Static-analysis finding validator (Enhancement 1).

For every raw scanner finding, decide whether the code actually supports it:

* SUPPORTED     — the unsafe pattern is independently reproduced on the line,
                  or two independent tools agree.
* CONTRADICTED  — the code already uses a safe pattern, the scanner match
                  cannot be reproduced, or the recommendation conflicts with a
                  repository policy.
* UNCERTAIN     — evidence is insufficient; escalate for human review.
* OUT_OF_SCOPE  — the finding is outside the reviewed change.

Statuses are PatchCourt-internal and are not SonarQube classifications.

Also tags each assessment with:
- fp_fn_root_cause / fp_fn_explanation  (from empirical FN/FP study: 7 root cause categories)
- fault_correlation                      (from SonarQube empirical fault study: high/medium/low)
"""
from __future__ import annotations

import re

from patchcourt.agents.schemas import Evidence, FindingAssessment
from patchcourt.adjudication.contextual import assess_context
from patchcourt.adjudication.correlate import correlation_index, corroborating_tools
from patchcourt.adjudication.rules import (
    Policy,
    category_for,
    load_repository_policies,
    match_policies,
    rule_for,
)
from patchcourt.tools.base import Finding


# ---------------------------------------------------------------------------
# FP/FN Root Cause Taxonomy
# (An Empirical Study of False Negatives and Positives of Static Code Analyzers)
# 7 categories: Flawed Rule Spec, Inconsistent Rule Implementation,
# Unhandled Language Features, Missing Cases, Mishandling IR,
# Analysis Module Error, General Programming Error, Miscellaneous
# ---------------------------------------------------------------------------
_FP_ROOT_CAUSES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "Flawed Rule Spec",
        "The rule definition is overly broad or imprecise, matching safe patterns.",
        ("safe", "false positive", "overly broad", "not applicable"),
    ),
    (
        "Inconsistent Rule Implementation",
        "The rule implementation diverges from its specification, producing spurious alerts.",
        ("implementation", "inconsistent", "mismatch", "spec"),
    ),
    (
        "Unhandled Language Features",
        "The analyzer does not handle a language construct used here (e.g. lambdas, generics).",
        ("lambda", "generic", "annotation", "reflection", "dynamic", "language feature"),
    ),
    (
        "Missing Cases",
        "The rule misses a variant of the unsafe pattern (false negative).",
        ("missing", "not detected", "variant", "indirect", "alias"),
    ),
    (
        "Mishandling Intermediate Representations",
        "The analyzer's IR transformation loses information, causing incorrect results.",
        ("ir", "ast", "bytecode", "intermediate", "cfg"),
    ),
    (
        "Analysis Module Error",
        "A bug in the analysis module (data-flow, taint, call-graph) produces wrong results.",
        ("data flow", "taint", "call graph", "inter-procedural", "flow"),
    ),
    (
        "General Programming Error",
        "A general implementation bug in the analyzer causes incorrect output.",
        ("bug", "crash", "exception", "null pointer", "index"),
    ),
]


def _fp_fn_root_cause(status: str, rationale: str, rule_id: str, category: str) -> tuple[str, str]:
    """Infer the most likely FP/FN root cause from the assessment context."""
    if status not in ("CONTRADICTED", "UNCERTAIN"):
        return "", ""
    text = f"{rationale} {rule_id} {category}".lower()
    for name, explanation, keywords in _FP_ROOT_CAUSES:
        if any(k in text for k in keywords):
            return name, explanation
    # Default for CONTRADICTED with no pattern match
    if status == "CONTRADICTED":
        return "Flawed Rule Spec", "Rule matched a safe pattern; likely overly broad specification."
    return "Missing Cases", "Pattern not reproduced; rule may miss this variant."


# ---------------------------------------------------------------------------
# Fault-Proneness Correlation
# (Some SonarQube Issues have a Significant but Small Effect on Faults)
# Rules empirically correlated with real faults get "high"; cosmetic rules get "low".
# ---------------------------------------------------------------------------
_HIGH_FAULT_RULES: frozenset[str] = frozenset({
    # Security — null dereference, resource leak, injection, hardcoded secrets
    "python:s2077", "python:s6042", "python:s2068", "python:s2076",
    "java:s2077", "java:s2068", "java:s2076",
    "b608", "b602", "b605", "b301", "b506",
    "sql_concat", "shell_true", "hardcoded_secret", "unsafe_deserial",
    # Null / resource
    "java:s2259", "java:s2095", "python:s1481",
})
_MEDIUM_FAULT_RULES: frozenset[str] = frozenset({
    "java:s1144", "java:s1172", "python:s1172",
    "complexity", "java:s3776", "python:s3776",
    "b105", "b106", "b107",
})


def _fault_correlation(rule: str, category: str) -> str:
    """Return empirical fault-correlation level for a rule."""
    r = (rule or "").lower()
    if r in _HIGH_FAULT_RULES or category == "security":
        return "high"
    if r in _MEDIUM_FAULT_RULES:
        return "medium"
    return "low"


def _search(patterns: tuple[str, ...], text: str) -> bool:
    if not text:
        return False
    return any(re.search(p, text) for p in patterns)


def _line_text(content: str, line: int) -> str:
    if not content or line < 1:
        return ""
    lines = content.splitlines()
    if line > len(lines):
        return ""
    return lines[line - 1]


def _code_snippet(content: str, line: int, context: int = 2) -> str:
    """Return a numbered context window of `context` lines either side of `line`."""
    if not content or line < 1:
        return ""
    lines = content.splitlines()
    start = max(0, line - 1 - context)
    end = min(len(lines), line + context)
    width = len(str(end + 1))
    parts = []
    for i, src in enumerate(lines[start:end], start=start + 1):
        marker = "→" if i == line else " "
        parts.append(f"{marker} {str(i).rjust(width)} | {src}")
    return "\n".join(parts)


def added_line_numbers(patch: str) -> set[int]:
    """Line numbers (in the new file) of added lines in a unified diff.

    Falls back to counting ``+``-prefixed lines when the patch has no hunk
    headers (the offline demo stores patches in that simplified form).
    """
    result: set[int] = set()
    if not patch:
        return result
    lines = patch.splitlines()
    new_no: int | None = None
    for raw in lines:
        if raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            new_no = int(m.group(1)) if m else None
            continue
        if new_no is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.add(new_no)
            new_no += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith("\\"):
            continue
        else:
            new_no += 1
    if not result:
        for i, raw in enumerate(lines, start=1):
            if raw.startswith("+") and not raw.startswith("+++"):
                result.add(i)
    return result


def touched_lines(patches: dict[str, str] | None) -> dict[str, set[int]]:
    return {f: added_line_numbers(p) for f, p in (patches or {}).items()}


def _classify_finding(
    file: str,
    line: int,
    head_contents: dict[str, str],
    base_contents: dict[str, str],
    touched: dict[str, set[int]],
) -> tuple[bool, bool]:
    """Return (introduced_by_pr, pre_existing) for a finding.

    introduced_by_pr — the flagged line is new: it appears in head but the
        base version of the file either doesn't exist (added file) or doesn't
        contain that exact line at that position.
    pre_existing — the flagged line existed verbatim in the base version,
        meaning the PR did not introduce it.

    Both can be False when the base file is unavailable (no token, binary,
    or the file was renamed in a way we couldn't resolve).
    """
    head_text = _line_text(head_contents.get(file, ""), line)
    if not head_text:
        return False, False

    base_content = base_contents.get(file, "")
    if not base_content:
        # File is new (added) or base unavailable — treat as introduced.
        return True, False

    base_lines = base_content.splitlines()
    # Check if the exact line text exists anywhere in the base file.
    # We use exact-text membership rather than line-number comparison because
    # surrounding insertions shift line numbers without changing the content.
    head_stripped = head_text.strip()
    base_has_line = any(bl.strip() == head_stripped for bl in base_lines)

    if not base_has_line:
        # Line content is new — introduced by this PR.
        return True, False

    # Line existed in base. Check if it was touched (moved/modified) by the PR.
    in_touched = line in touched.get(file, set())
    if in_touched:
        # The diff touched this line number but the content is the same —
        # context line that was shifted; treat as pre-existing.
        return False, True

    return False, True


def _text(finding: Finding) -> str:
    return " ".join([finding.rule or "", finding.message or "", finding.recommendation or ""])


def _is_visibility_widening(finding: Finding) -> bool:
    text = _text(finding).lower()
    if "visibilit" not in text and "public" not in text:
        return False
    return any(k in text for k in ("make", "public", "widen", "increase", "should be", "private"))


def _policy_forbids_widening(refs: list) -> bool:
    for ref in refs:
        blob = f"{ref.id} {ref.title} {ref.excerpt}".lower()
        if "api-boundaries" in blob or "boundar" in blob:
            return True
        if "remain private" in blob or "context-dependent" in blob:
            return True
    return False


class FindingValidator:
    """Adjudicates raw scanner findings against code and repository policies."""

    def __init__(self, policies: list[Policy] | None = None) -> None:
        self.policies = list(policies) if policies is not None else load_repository_policies()

    def validate(
        self,
        findings: list[Finding],
        file_contents: dict[str, str] | None = None,
        correlations: list | None = None,
        patches: dict[str, str] | None = None,
        base_file_contents: dict[str, str] | None = None,
    ) -> list[FindingAssessment]:
        file_contents = file_contents or {}
        base_file_contents = base_file_contents or {}
        groups = correlation_index(correlations or [])
        touched = touched_lines(patches) if patches else {}
        return [
            self._assess(f, file_contents, groups, touched, base_file_contents)
            for f in findings
        ]

    def _assess(self, finding: Finding, file_contents, groups, touched, base_file_contents=None) -> FindingAssessment:
        rule = rule_for(finding)
        category = category_for(finding, rule)
        line_text = _line_text(file_contents.get(finding.file, ""), finding.line)
        snippet = _code_snippet(file_contents.get(finding.file, ""), finding.line)
        introduced, pre_existing = _classify_finding(
            finding.file, finding.line,
            file_contents, base_file_contents or {}, touched,
        )
        key = (finding.file, int(finding.line or 0))
        group = groups.get(key)
        corro = corroborating_tools(group, finding.tool)
        refs = match_policies(_text(finding), self.policies) if self.policies else []

        danger = _search(rule.dangerous_patterns, line_text) if rule else False
        safe = _search(rule.safe_patterns, line_text) if rule else False
        rationale = ""

        if file_contents and finding.file not in file_contents:
            status = "OUT_OF_SCOPE"
            rationale = f"{finding.file} is not part of this change."
        elif category == "maintainability":
            status, rationale = self._assess_maintainability(finding, refs)
        elif not line_text:
            status = "UNCERTAIN"
            rationale = "flagged line could not be resolved in the provided content."
        elif rule is None:
            if corro:
                status = "SUPPORTED"
                rationale = f"rule not catalogued; two tools agree ({', '.join(corro)})."
            else:
                status = "UNCERTAIN"
                rationale = "rule not catalogued and no independent corroboration."
        elif danger and not safe:
            status = "SUPPORTED"
            rationale = "unsafe pattern independently reproduced on the flagged line."
        elif safe:
            status = "CONTRADICTED"
            rationale = "code already uses a safe pattern on the flagged line."
        elif corro:
            status = "UNCERTAIN"
            rationale = (
                "scanner match not reproduced on the line, but an independent tool agrees — "
                "requires deeper review."
            )
        else:
            status = "CONTRADICTED"
            rationale = "scanner match could not be reproduced on the flagged line."

        # A pre-existing finding on an untouched line is lower priority than
        # one the PR actually introduced. Use introduced_by_pr when available,
        # fall back to the patch-based touched check.
        if introduced:
            pr_touched = True
        elif pre_existing:
            pr_touched = False
        else:
            pr_touched = finding.line in touched.get(finding.file, set()) if touched else True
        priority, action = assess_context(
            status=status,
            category=category,
            severity=finding.severity,
            file=finding.file,
            line_text=line_text,
            safeguard=safe,
            pr_touched=pr_touched,
        )

        evidence = [
            Evidence(tier=1, text=f"[{finding.tool}] {finding.rule or 'rule'}: {finding.message}"[:500])
        ]
        if corro:
            # Only list other, independent tools (exclude self)
            other_tools = [t for t in corro if t != finding.tool]
            if other_tools:
                evidence.append(
                    Evidence(tier=2, text=f"corroborated by {', '.join(other_tools)} on {finding.file}:{finding.line}")
                )
            else:
                evidence.append(
                    Evidence(tier=2, text=f"corroborated on {finding.file}:{finding.line}")
                )
        if status == "SUPPORTED" and category == "security":
            evidence.append(
                Evidence(tier=1, text=f"pattern independently reproduced on {finding.file}:{finding.line}")
            )
        if safe:
            evidence.append(Evidence(tier=1, text="safe pattern present on the flagged line"))
        for ref in refs:
            evidence.append(Evidence(tier=3, text=f"repo policy {ref.id}: {ref.title}"))

        fp_fn_cause, fp_fn_expl = _fp_fn_root_cause(
            status, rationale, finding.rule or "", category
        )
        fault_corr = _fault_correlation(finding.rule or "", category)

        return FindingAssessment(
            tool=finding.tool,
            file=finding.file,
            line=finding.line,
            rule=finding.rule,
            message=finding.message,
            severity=finding.severity,
            category=category,
            status=status,
            rationale=rationale,
            corroborated=bool(corro),
            corroborating_tools=corro,
            policies=refs,
            contextual_priority=priority,
            contextual_action=action,
            evidence=evidence,
            fp_fn_root_cause=fp_fn_cause,
            fp_fn_explanation=fp_fn_expl,
            fault_correlation=fault_corr,
            code_snippet=snippet,
            introduced_by_pr=introduced,
            pre_existing=pre_existing,
        )

    def _assess_maintainability(self, finding: Finding, refs: list) -> tuple[str, str]:
        if _is_visibility_widening(finding) and _policy_forbids_widening(refs):
            return (
                "CONTRADICTED",
                "Repository policy keeps internal members private; widening visibility is only "
                "justified when an external caller actually requires access.",
            )
        if refs:
            return (
                "UNCERTAIN",
                "Maintainability recommendation — adjudicate against the matched repository "
                "standards before acting.",
            )
        return (
            "UNCERTAIN",
            "Context-dependent maintainability recommendation; needs review against repository design.",
        )


def validate_findings(
    findings: list[Finding],
    file_contents: dict[str, str] | None = None,
    correlations: list | None = None,
    patches: dict[str, str] | None = None,
    policies: list[Policy] | None = None,
    base_file_contents: dict[str, str] | None = None,
) -> list[FindingAssessment]:
    return FindingValidator(policies=policies).validate(
        findings,
        file_contents=file_contents,
        correlations=correlations,
        patches=patches,
        base_file_contents=base_file_contents,
    )
