"""Conflict detection — find disagreeing claims to feed the debate stage."""
from __future__ import annotations

from collections import defaultdict

from patchcourt.agents.schemas import Claim


def _issue_tokens(claim: Claim) -> set[str]:
    return {t for t in claim.issue.lower().replace(",", " ").split() if len(t) > 2}


def same_claim(a: Claim, b: Claim, issue_ft: float = 0.6, file_ft: float = 0.5) -> bool:
    """Test whether two claims refer to the same underlying issue.

    Same file is required; issue stems are compared by common tokens.
    """
    if a.file != b.file:
        return False
    tokens_a = _issue_tokens(a)
    tokens_b = _issue_tokens(b)
    if not tokens_a or not tokens_b:
        return a.line == b.line
    overlap = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
    return overlap >= issue_ft


def _group_key(claim: Claim) -> tuple:
    """Claims cluster on (file, line) when a line is known, else on issue tokens."""
    if claim.line > 0:
        return (claim.file, int(claim.line))
    return (claim.file, tuple(sorted(_issue_tokens(claim))))


def detect_conflicts(claims: list[Claim]) -> list[dict]:
    """Disputes need >= 2 agents covering the same location with differing severity."""
    grouped: dict[tuple, list[Claim]] = defaultdict(list)
    for c in claims:
        grouped[_group_key(c)].append(c)

    conflicts: list[dict] = []
    for key, group in grouped.items():
        agents = {c.agent for c in group}
        if len(agents) < 2:
            continue
        sevs = sorted({c.severity for c in group})
        if len(sevs) < 2:
            continue
        conflicts.append(
            {
                "file": group[0].file,
                "line": group[0].line,
                "claims": group,
                "type": "disputed",
                "reason": f"agents disagree on severity ({sevs}) for {group[0].file}:{group[0].line}",
            }
        )
    return conflicts