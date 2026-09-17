"""Judge module — scoring and verdicts."""
from patchcourt.judge.scoring import (
    claim_score,
    corroboration_factor,
    build_report,
    verdict_for,
    avg_evidence_tier,
    best_case_tier,
)

__all__ = [
    "claim_score",
    "corroboration_factor",
    "build_report",
    "verdict_for",
    "avg_evidence_tier",
    "best_case_tier",
]