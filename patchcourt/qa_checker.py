"""QA-Checker agent — validates debate conclusions before finalizing verdicts.

Inspired by CodeAgent (autonomous communicative agents for code review):
a third agent reviews the debate output and checks whether the conclusion is
internally consistent with the evidence tier and rationale.

Three possible verdicts:
  VALID        — conclusion is consistent with the evidence; proceed.
  INCONSISTENT — conclusion contradicts the evidence tier (e.g. BLOCK on T5-only).
  NEEDS_REWORK — rationale is too vague or missing; one more debate round needed.

If the QA-Checker returns NEEDS_REWORK, the debate engine triggers one
additional round with the rejection reason injected as context.
"""
from __future__ import annotations

import logging
import re

from patchcourt.agents.schemas import DebatedClaim, FindingAssessment

logger = logging.getLogger("patchcourt.qa_checker")

# ---------------------------------------------------------------------------
# Consistency rules (deterministic — no LLM needed)
# ---------------------------------------------------------------------------

_VAGUE_PATTERNS = re.compile(
    r"\b(unclear|unknown|possibly|might|could be|not sure|no information|n/a)\b",
    re.IGNORECASE,
)


def _is_t5_only(debated: DebatedClaim) -> bool:
    claim = debated.claim
    if not claim.evidence:
        return True
    return all(e.tier == 5 for e in claim.evidence)


def _verdict_from_summary(summary: str) -> str:
    s = (summary or "").upper()
    if "BLOCK" in s:
        return "BLOCK"
    if "NEEDS_REVIEW" in s or "REVIEW" in s:
        return "NEEDS_REVIEW"
    return "MERGE"


def _check_t5_block(debated: DebatedClaim) -> tuple[str, str]:
    """BLOCK must never rest on T5 evidence alone."""
    implied = _verdict_from_summary(debated.verdict_summary)
    if implied == "BLOCK" and _is_t5_only(debated):
        return (
            "INCONSISTENT",
            "Debate concluded BLOCK but all evidence is T5 (LLM-only). "
            "Hard constraint violated: BLOCK requires at least one T1/T2 finding. "
            "Downgrade to NEEDS_REVIEW.",
        )
    return "", ""


def _check_rationale_vagueness(debated: DebatedClaim) -> tuple[str, str]:
    """Rationale must not be empty or purely vague."""
    summary = debated.verdict_summary or ""
    if not summary.strip():
        return (
            "NEEDS_REWORK",
            "Verdict summary is empty. A developer-facing explanation is required.",
        )
    if _VAGUE_PATTERNS.search(summary) and len(summary.split()) < 12:
        return (
            "NEEDS_REWORK",
            f"Verdict summary is too vague: '{summary[:80]}'. "
            "Name the specific identifier, file:line, and recommended action.",
        )
    return "", ""


def _check_evidence_tier_consistency(debated: DebatedClaim) -> tuple[str, str]:
    """High-severity claims should have supporting evidence, not just T5."""
    claim = debated.claim
    if claim.severity >= 4 and _is_t5_only(debated):
        return (
            "INCONSISTENT",
            f"Severity {claim.severity}/5 claim '{claim.issue[:60]}' rests on T5 evidence only. "
            "Severity should be reduced or the claim needs tool corroboration.",
        )
    return "", ""


def _check_supporting_opposing_balance(debated: DebatedClaim) -> tuple[str, str]:
    """Both sides must have made a substantive argument."""
    if not (debated.supporting or "").strip():
        return (
            "NEEDS_REWORK",
            "Prosecution argument is empty — debate did not produce a supporting statement.",
        )
    if not (debated.opposing or "").strip():
        return (
            "NEEDS_REWORK",
            "Defense argument is empty — debate did not produce an opposing statement.",
        )
    return "", ""


_CHECKS = [
    _check_t5_block,
    _check_evidence_tier_consistency,
    _check_rationale_vagueness,
    _check_supporting_opposing_balance,
]


def qa_check_debate(debated: DebatedClaim) -> tuple[str, str]:
    """Run all QA checks on a debated claim.

    Returns ``(verdict, note)`` where verdict is one of:
      VALID / INCONSISTENT / NEEDS_REWORK
    """
    for check in _CHECKS:
        verdict, note = check(debated)
        if verdict:
            logger.info(
                "QA-Checker: %s for %s:%s — %s",
                verdict, debated.claim.file, debated.claim.line, note[:80],
            )
            return verdict, note
    return "VALID", ""


def qa_check_assessment(assessment: FindingAssessment) -> tuple[str, str]:
    """QA-check a FindingAssessment for internal consistency.

    Validates that:
    - SUPPORTED findings have at least one T1/T2 evidence item
    - CONTRADICTED findings have a non-empty rationale
    - contextual_action == 'block' only when status == 'SUPPORTED'
    """
    status = assessment.status
    action = assessment.contextual_action
    rationale = assessment.rationale or ""
    evidence_tiers = [e.tier for e in assessment.evidence]
    best_tier = min(evidence_tiers) if evidence_tiers else 5

    if status == "SUPPORTED" and best_tier > 2:
        return (
            "INCONSISTENT",
            f"SUPPORTED status but best evidence tier is T{best_tier} — "
            "needs T1/T2 tool evidence to be marked SUPPORTED.",
        )
    if status == "CONTRADICTED" and not rationale.strip():
        return (
            "NEEDS_REWORK",
            "CONTRADICTED status has no rationale — explain why the finding was contradicted.",
        )
    if action == "block" and status != "SUPPORTED":
        return (
            "INCONSISTENT",
            f"contextual_action=block but status={status}. "
            "BLOCK action is only valid for SUPPORTED findings.",
        )
    return "VALID", ""


def run_qa_checks(
    debated_claims: list[DebatedClaim],
    assessments: list[FindingAssessment],
) -> tuple[list[DebatedClaim], list[FindingAssessment]]:
    """Apply QA-Checker to all debated claims and assessments.

    Mutates ``qa_verdict`` and ``qa_note`` on each assessment in-place.
    Returns the same lists (modified) for chaining.
    """
    for dc in debated_claims:
        verdict, note = qa_check_debate(dc)
        # Patch verdict_summary if INCONSISTENT (downgrade BLOCK → NEEDS_REVIEW)
        if verdict == "INCONSISTENT" and "BLOCK" in (dc.verdict_summary or "").upper():
            dc.verdict_summary = dc.verdict_summary.replace("BLOCK", "NEEDS_REVIEW")
            dc.verdict_summary += f" [QA-Checker: {note}]"

    for a in assessments:
        verdict, note = qa_check_assessment(a)
        a.qa_verdict = verdict
        a.qa_note = note

    return debated_claims, assessments
