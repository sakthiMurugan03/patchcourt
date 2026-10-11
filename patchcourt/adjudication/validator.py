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
    ) -> list[FindingAssessment]:
        file_contents = file_contents or {}
        groups = correlation_index(correlations or [])
        touched = touched_lines(patches) if patches else {}
        return [self._assess(f, file_contents, groups, touched) for f in findings]

    def _assess(self, finding: Finding, file_contents, groups, touched) -> FindingAssessment:
        rule = rule_for(finding)
        category = category_for(finding, rule)
        line_text = _line_text(file_contents.get(finding.file, ""), finding.line)
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

        return FindingAssessment(
            tool=finding.tool,
            file=finding.file,
            line=finding.line,
            rule=finding.rule,
            message=finding.message,
            category=category,
            status=status,
            rationale=rationale,
            corroborated=bool(corro),
            corroborating_tools=corro,
            policies=refs,
            contextual_priority=priority,
            contextual_action=action,
            evidence=evidence,
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
) -> list[FindingAssessment]:
    return FindingValidator(policies=policies).validate(
        findings, file_contents=file_contents, correlations=correlations, patches=patches
    )
