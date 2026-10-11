"""Contextual severity and priority (Enhancement 4).

The scanner's severity is preserved; this module adds an *additional*
contextual priority derived from reachability, security sensitivity, existing
safeguards, and whether the flagged line is part of the change under review.
"""
from __future__ import annotations

from patchcourt.agents.schemas import FindingAssessment

_SENSITIVE_HINTS = (
    "auth",
    "crypto",
    "password",
    "secret",
    "token",
    "session",
    "login",
    "sql",
    "db",
    "database",
    "query",
    "payment",
    "admin",
)


def is_reachable(line_text: str) -> bool:
    stripped = (line_text or "").strip().lstrip("+")
    if not stripped:
        return False
    return not stripped.startswith(("#", "//", "/*", "*"))


def is_security_sensitive(category: str, file: str) -> bool:
    if category == "security":
        return True
    lowered = (file or "").lower()
    return any(hint in lowered for hint in _SENSITIVE_HINTS)


def assess_context(
    *,
    status: str,
    category: str,
    severity: int,
    file: str,
    line_text: str,
    safeguard: bool,
    pr_touched: bool,
) -> tuple[str, str]:
    """Return ``(priority, recommended_action)`` for an assessment."""
    if status == "OUT_OF_SCOPE":
        return "info", "acknowledge"
    if status == "CONTRADICTED":
        return "info", "acknowledge"
    if status == "UNCERTAIN":
        return "low", "human_review"

    reachable = is_reachable(line_text)
    sensitive = is_security_sensitive(category, file)

    if category == "security":
        if safeguard:
            return "medium", "review"
        if reachable and sensitive and severity >= 5:
            return "critical", "block"
        if reachable and sensitive:
            return "high", "remediate"
        if reachable:
            return "medium", "remediate"
        return "low", "review"

    if severity >= 4 and reachable and pr_touched:
        return "high", "remediate"
    if reachable:
        return "medium", "review"
    return "low", "acknowledge"


def summarize(assessments: list[FindingAssessment]) -> dict:
    """Aggregate contextual priorities across a review."""
    by_priority: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for a in assessments:
        by_priority[a.contextual_priority] = by_priority.get(a.contextual_priority, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1
        by_action[a.contextual_action] = by_action.get(a.contextual_action, 0) + 1
    blocking = sum(1 for a in assessments if a.contextual_action == "block")
    return {
        "total": len(assessments),
        "by_priority": by_priority,
        "by_status": by_status,
        "by_action": by_action,
        "blocking": blocking,
    }
