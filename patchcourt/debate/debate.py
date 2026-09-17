"""Bounded evidence-gated debate. Max 2 rounds, RAG-fresh rebuttals."""
from __future__ import annotations

from patchcourt.agents.schemas import DebatedClaim
from patchcourt.config import settings
from patchcourt.rag.store import query


def _tier(tag: str) -> int:
    for t in range(1, 6):
        if f"T{t}" in tag.upper():
            return t
    return 3


def run_debate(conflicts: list[dict], pr) -> list[DebatedClaim]:
    """Run a bounded debate over conflicting claims.

    Deterministic when no real LLM is available: agents produce rebuttals
    from retrieved evidence only; rounds are capped at ``debate_max_rounds``.
    """
    resolved: list[DebatedClaim] = []
    for conflict in conflicts:
        claim: Claim = conflict["claims"][0]
        opponent: Claim = conflict["claims"][-1]
        base = DebatedClaim(
            claim=claim,
            supporting=claim.issue,
            opposing=opponent.issue,
            rounds=0,
        )

        for round_no in range(min(settings.debate_max_rounds, 2)):
            base.rounds = round_no + 1
            ctx = query(claim.issue, n_results=5)
            if not ctx:
                break
            fresh = " ".join(r["document"][:300] for r in ctx[:3])

            if opp_max := max((e.tier for e in opponent.evidence), default=5) <= _tier(
                "T2"
            ):
                easy = opp_max <= 3
                if easy:
                    base.supporting = (
                        f"R{round_no+1} — defense reinforced by during-debate retrieval: {fresh}"
                    )
                    base.opposing = f"R{round_no+1} — opponent downgraded, evidence is only T{opp_max}."
                    break
            base.supporting = f"R{round_no+1} — retrieved evidence for claim: {fresh}"
            base.opposing = (
                f"R{round_no+1} — defender argues severity; counter-evidence has no T1/T2 proof."
            )
        resolved.append(base)
    return resolved