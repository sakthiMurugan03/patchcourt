"""Judge module — deterministic scoring and verdict."""
from __future__ import annotations

from patchcourt.agents.schemas import Claim, FileReport, ReviewReport
from patchcourt.config import TIER_WEIGHTS


def claim_score(claim: Claim, corroboration: float = 1.0) -> float:
    """score = severity × tier_weight × corroboration × confidence"""
    return (
        claim.severity
        * TIER_WEIGHTS[claim.tier]
        * corroboration
        * claim.confidence
    )


def corroboration_factor(claims: list[Claim], claim: Claim) -> float:
    """Extra multiplier from agreement across independent agents."""
    same_file = [c for c in claims if c.file == claim.file and c.agent != claim.agent]
    if not same_file:
        return 1.0
    supporting = sum(1 for c in same_file if _agree(c, claim))
    return 1.0 + 0.25 * supporting if supporting else 1.0


def _agree(a: Claim, b: Claim) -> bool:
    ta, tb = set(a.issue.lower().split()), set(b.issue.lower().split())
    if not ta or not tb:
        return a.file == b.file
    return a.file == b.file and bool(ta & tb)


def avg_evidence_tier(claim: Claim) -> float:
    if not claim.evidence:
        return 0.0
    return sum(e.tier for e in claim.evidence) / len(claim.evidence)


def best_case_tier(claim: Claim) -> int:
    """Most favorable (lowest) tier among the claim's evidence tags."""
    return min((e.tier for e in claim.evidence), default=claim.tier)


def is_t5_only(claim: Claim) -> bool:
    """A claim rests on T5 evidence alone iff every evidence item is T5."""
    if not claim.evidence:
        return True
    return all(e.tier == 5 for e in claim.evidence)


def block_allowed(non_t5_score: float, block_threshold: float = 10.0) -> bool:
    """HARD CONSTRAINT: a BLOCK verdict can never rest on T5 evidence alone."""
    return non_t5_score >= block_threshold


def safe_verdict(
    overall_score: float,
    non_t5_score: float,
    block_threshold: float = 10.0,
    needs_review: float = 4.0,
) -> str:
    """Verdict with the T5-alone BLOCK constraint enforced."""
    if overall_score >= block_threshold:
        if block_allowed(non_t5_score, block_threshold):
            return "BLOCK"
        return "NEEDS_REVIEW"  # BLOCK would rest on T5 alone → downgraded
    if overall_score >= needs_review:
        return "NEEDS_REVIEW"
    return "MERGE"


def verdict_for(score: float, block_threshold: float = 10.0, needs_review: float = 4.0) -> str:
    if score >= block_threshold:
        return "BLOCK"
    if score >= needs_review:
        return "NEEDS_REVIEW"
    return "MERGE"


def _score(claims: list[Claim]) -> float:
    return round(
        sum(claim_score(c, corroboration_factor(claims, c)) for c in claims), 2
    )


def build_report(pr_url: str, claims: list[Claim], debates: list) -> ReviewReport:
    report = ReviewReport(pr_url=pr_url, claims=claims)
    per_file: dict[str, list[Claim]] = {}
    for c in claims:
        per_file.setdefault(c.file, []).append(c)

    total = 0.0
    non_t5_total = 0.0
    for fname, fclaims in per_file.items():
        fs = _score(fclaims)
        total += fs
        non_t5_fs = _score([c for c in fclaims if not is_t5_only(c)])
        non_t5_total += non_t5_fs
        report.files.append(FileReport(file=fname, claims=fclaims, score=fs))

    report.overall_score = round(total, 2)
    report.verdict = safe_verdict(round(total, 2), round(non_t5_total, 2))
    report.debate_transcripts = [
        {
            "file": d.claim.file,
            "issue": d.claim.issue,
            "supporting": d.supporting,
            "opposing": d.opposing,
            "rounds": d.rounds,
        }
        for d in debates
    ]
    return report