"""Bounded evidence-gated debate. Max 2 rounds, RAG-fresh rebuttals."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from patchcourt.agents.schemas import Claim, DebatedClaim
from patchcourt.config import settings
from patchcourt.runtime_llm_config import get_runtime_config

logger = logging.getLogger("patchcourt.debate")

try:
    from patchcourt.llm import get_llm
    _LLM_AVAILABLE = True
except Exception:
    _LLM_AVAILABLE = False


def _tier(tag: str) -> int:
    for t in range(1, 6):
        if f"T{t}" in tag.upper():
            return t
    return 3


def _source_label(claim: Claim) -> str:
    """Return a short label for the claim's source."""
    if claim.source == "tool":
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
        import re
        m = re.search(r"\b([A-Z][A-Z0-9]{2,}|B\d{3}|SEC-\d+|[A-Z]{2,}-\d+)\b", t)
        if m:
            return f"rule {m.group(1)}"
    return "rule"


def _evidence_summary(claim: Claim) -> str:
    """Summarize the claim's evidence tiers."""
    tiers = [e.tier for e in claim.evidence]
    if not tiers:
        return "no evidence"
    best = min(tiers)
    return f"best tier T{best}"


def _build_prosecution_prompt(claim: Claim, opponent: Claim) -> str:
    """Build prompt for prosecution argument."""
    source = _source_label(claim)
    rule = _rule_snippet(claim)
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    sev = sev_labels.get(claim.severity, "medium")
    tier = f"T{claim.tier}"
    ev_summary = _evidence_summary(claim)

    return (
        f"You are the PROSECUTION in a code review debate. State the charge clearly.\n\n"
        f"Claim: {claim.issue}\n"
        f"Location: {loc}\n"
        f"Source: {source}\n"
        f"Severity: {claim.severity}/{sev}\n"
        f"Tier: T{claim.tier}\n"
        f"Evidence: {_evidence_summary(claim)}\n\n"
        f"Opposing claim: {opponent.issue}\n"
        f"Opposing tier: T{opponent.tier}\n\n"
        f"Write 1-2 sentences stating the charge in plain language + why it matters (the risk). "
        f"Cite the tool/rule/file:line and tier. Do NOT just restate the rule text."
    )


def _build_defense_prompt(claim: Claim, opponent: Claim) -> str:
    """Build prompt for defense argument."""
    opp_source = _source_label(opponent)
    opp_rule = _rule_snippet(opponent)
    opp_loc = f"{opponent.file}:{opponent.line}" if opponent.line else opponent.file

    return (
        f"You are the DEFENSE in a code review debate. Make a REAL REBUTTAL.\n\n"
        f"Your claim: {claim.issue}\n"
        f"Your tier: T{claim.tier}\n"
        f"Opposing claim: {opponent.issue}\n"
        f"Opposing location: {opponent.file}:{opponent.line if opponent.line else '?'}\n"
        f"Opposing source: {opponent.source}\n"
        f"Opposing tier: T{opponent.tier}\n\n"
        f"Choose ONE of these strategies and write 1-2 sentences:\n"
        f"(a) Argue MITIGATION/CONTEXT — e.g., 'used with a fixed command, not user input, so injection risk is limited'\n"
        f"(b) Note LACK OF CORROBORATION — e.g., 'no corroborating T1/T2 evidence, so severity should not escalate'\n"
        f"(c) CONCEDE — e.g., 'finding stands; recommend fixing before merge'\n\n"
        f"DO NOT just restate the prosecution's rule text. Make a distinct argument."
    )


async def _llm_debate_round(claim: Claim, opponent: Claim, round_no: int) -> tuple[str, str]:
    """Generate both sides via LLM for a debate round."""
    if not _LLM_AVAILABLE:
        raise RuntimeError("LLM not available")

    llm = get_llm()
    if llm._use_mock:
        raise RuntimeError("LLM is in mock mode")

    prosecution_prompt = _build_prosecution_prompt(claim, opponent)
    defense_prompt = _build_defense_prompt(claim, opponent)

    try:
        # Generate prosecution
        prosecution_resp = await llm.generate(
            "You are the prosecution in a code review debate.",
            prosecution_prompt
        )
        prosecution = prosecution_resp.get("claims", [{}])[0].get("issue", "")

        # Generate defense
        defense_resp = await llm.generate(
            "You are the defense in a code review debate.",
            defense_prompt
        )
        defense = defense_resp.get("claims", [{}])[0].get("issue", "")

        return prosecution, defense
    except Exception as e:
        logger.warning("LLM debate generation failed: %s", e)
        raise


def _format_prosecution_mock(claim: Claim, round_no: int) -> str:
    """Format prosecution statement (mock mode)."""
    source = _source_label(claim)
    rule = _rule_snippet(claim)
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    sev = sev_labels.get(claim.severity, "medium")
    tier = f"T{claim.tier}"

    if round_no == 1:
        return (
            f"{source} {rule} flags {claim.issue} at {loc} — "
            f"risk: {claim.issue.lower()} could lead to security/exploit issues "
            f"(severity {claim.severity}/{sev}, T{claim.tier})."
        )
    else:
        return (
            f"R{round_no} — {source} still flags {claim.issue} at {loc}; "
            f"no new evidence reduces the risk (T{claim.tier})."
        )


def _format_defense_mock(claim: Claim, opponent: Claim, round_no: int) -> str:
    """Format defense rebuttal (mock mode) — genuinely different from prosecution."""
    opp_source = _source_label(opponent)
    opp_rule = _rule_snippet(opponent)
    opp_loc = f"{opponent.file}:{opponent.line}" if opponent.line else opponent.file
    opp_max_tier = max((e.tier for e in opponent.evidence), default=5)
    opp_has_strong = opp_max_tier <= 2

    # Determine defense strategy based on claim properties
    claim_type = claim.issue.lower()
    has_context = any(
        "fixed" in e.text.lower() or "hardcoded" in e.text.lower() or "constant" in e.text.lower()
        for e in claim.evidence
    )
    has_corroboration = claim.corroborated or any(e.tier <= 2 for e in claim.evidence)

    if round_no == 1:
        if opp_has_strong:
            # Opponent has strong evidence - acknowledge but contextualize
            return (
                f"{opponent.issue} at {opp_loc} is corroborated (T{opp_max_tier}). "
                f"However, the risk is mitigated because the code uses a fixed command pattern, "
                f"not dynamic user input — injection vector is limited."
            )
        elif has_context:
            # Argue mitigation
            return (
                f"Finding stands but severity overstated: the code uses a fixed/hardcoded value, "
                f"not user-controlled input, so injection risk is minimal."
            )
        elif not has_corroboration:
            # Argue lack of corroboration
            return (
                f"No T1/T2 corroborating evidence from {opponent.source} "
                f"(max tier T{opp_max_tier}); severity should not escalate beyond T{claim.tier}."
            )
        else:
            # Concede
            return (
                f"Finding stands — recommend fixing before merge. "
                f"No strong mitigation identified."
            )
    else:
        if opp_has_strong:
            return (
                f"R{round_no} — {opponent.source} still corroborates with T{opp_max_tier} evidence; "
                f"finding confirmed."
            )
        else:
            return (
                f"R{round_no} — opponent lacks T1/T2 proof (best T{opp_max_tier}); "
                f"original claim at T{claim.tier} stands without escalation."
            )


async def _debate_round(claim: Claim, opponent: Claim, round_no: int) -> tuple[str, str]:
    """Run a single debate round, using LLM if available."""
    # Check if we should use real LLM - check runtime config for effective settings
    runtime_cfg = get_runtime_config()
    use_llm = (
        not runtime_cfg.use_mock_llm
        and runtime_cfg.provider != "mock"
        and _LLM_AVAILABLE
    )

    if use_llm:
        try:
            return await _llm_debate_round(claim, opponent, round_no)
        except Exception as e:
            logger.warning("LLM debate failed, falling back to mock: %s", e)

    # Mock mode fallback
    return _format_prosecution_mock(claim, round_no), _format_defense_mock(claim, opponent, round_no)


async def run_debate(conflicts: list[dict], pr) -> list[DebatedClaim]:
    """Run a bounded debate over conflicting claims.

    Uses real LLM when LLM_PROVIDER != mock, falls back to improved mock templates.
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

            supporting, opposing = await _debate_round(claim, opponent, round_no)
            base.supporting = supporting
            base.opposing = opposing

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