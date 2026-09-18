"""Bounded evidence-gated debate. Max 2 rounds, RAG-fresh rebuttals."""
from __future__ import annotations

from patchcourt.agents.schemas import Claim, DebatedClaim
from patchcourt.config import settings


def _tier(tag: str) -> int:
    for t in range(1, 6):
        if f"T{t}" in tag.upper():
            return t
    return 3


def _source_label(claim: Claim) -> str:
    """Return a short label for the claim's source."""
    if claim.source == "tool":
        # Try to extract tool name from evidence
        for e in claim.evidence:
            t = e.text.lower()
            if "bandit" in t:
                return "Bandit"
            if "semgrep" in t:
                return "Semgrep"
            if "gitleaks" in t:
                return "Gitleaks"
            if "radon" in t:
                return "Radon"
        return "Static analysis"
    return claim.agent.capitalize()


def _rule_snippet(claim: Claim) -> str:
    """Extract rule ID from evidence if available."""
    for e in claim.evidence:
        t = e.text
        # Look for common rule patterns
        import re
        m = re.search(r"\b([A-Z][A-Z0-9]{2,}|B\d{3}|SEC-\d+|[A-Z]{2,}-\d+)\b", t)
        if m:
            return f"rule {m.group(1)}"
    return "rule"


def _format_prosecution(claim: Claim, round_no: int) -> str:
    """Format a clean prosecution statement for the round."""
    source = _source_label(claim)
    rule = _rule_snippet(claim)
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    sev = sev_labels.get(claim.severity, "medium")
    tier = f"T{claim.tier}"
    corr = "corroborated" if claim.corroborated else "unbacked"

    if round_no == 1:
        return (
            f"{source} {rule} flags an issue at {loc} — "
            f"{claim.issue} (severity {claim.severity}/{sev}, {tier}, {corr})."
        )
    else:
        return (
            f"R{round_no} — {source} {rule} at {loc} still indicates "
            f"{claim.issue} (severity {claim.severity}/{sev}, {tier})."
        )


def _format_defense(claim: Claim, opponent: Claim, round_no: int) -> str:
    """Format a clean defense rebuttal for the round."""
    opp_max_tier = max((e.tier for e in opponent.evidence), default=5)
    opp_source = _source_label(opponent)
    opp_rule = _rule_snippet(opponent)
    opp_loc = f"{opponent.file}:{opponent.line}" if opponent.line else opponent.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    opp_sev = sev_labels.get(opponent.severity, "medium")

    # Determine if opponent has strong evidence (T1/T2)
    opp_has_strong = opp_max_tier <= 2

    if round_no == 1:
        if opp_has_strong:
            return (
                f"{opp_source} {opp_rule} at {opp_loc} corroborates "
                f"(severity {opponent.severity}/{opp_sev}, T{opp_max_tier}) — "
                f"finding stands, severity not escalated."
            )
        else:
            return (
                f"No corroborating T1/T2 counter-evidence from {opp_source} "
                f"(max tier T{opp_max_tier}); the finding stands, "
                f"severity not escalated."
            )
    else:
        if opp_has_strong:
            return (
                f"R{round_no} — {opp_source} still corroborates at {opp_loc} "
                f"with T{opp_max_tier} evidence."
            )
        else:
            return (
                f"R{round_no} — opponent lacks T1/T2 proof (best T{opp_max_tier}); "
                f"original claim not downgraded."
            )


def run_debate(conflicts: list[dict], pr) -> list[DebatedClaim]:
    """Run a bounded debate over conflicting claims.

    Deterministic when no real LLM is available: agents produce rebuttals
    from structured claim fields only; rounds are capped at ``debate_max_rounds``.
    """
    resolved: list[DebatedClaim] = []
    for conflict in conflicts:
        claim: Claim = conflict["claims"][0]
        opponent: Claim = conflict["claims"][-1]
        base = DebatedClaim(
            claim=claim,
            supporting="",
            opposing="",
            rounds=0,
        )

        for round_no in range(min(settings.debate_max_rounds, 2)):
            base.rounds = round_no + 1

            base.supporting = _format_prosecution(claim, round_no)
            base.opposing = _format_defense(claim, opponent, round_no)

            # Check if opponent has strong evidence to stop early
            opp_max_tier = max((e.tier for e in opponent.evidence), default=5)
            if opp_max_tier <= _tier("T2") and opp_max_tier <= 3:
                # Opponent has strong evidence — debate resolved
                base.supporting = (
                    f"R{round_no+1} — defense acknowledged; "
                    f"{_source_label(opponent)} corroborates with T{opp_max_tier} evidence."
                )
                base.opposing = (
                    f"R{round_no+1} — opponent's evidence confirmed at T{opp_max_tier}; "
                    f"no further rebuttal needed."
                )
                break

        resolved.append(base)
    return resolved