"""Evidence Engine — runs analysis tools before the LLM agents and normalizes
findings into tiered claims.

Tier assignment (deterministic):
  T1 = 1.0  a tool flags a specific file/line
  T2 = 0.8  two tools agree on the same line
  T3 = 0.5  repo policy surfaced via RAG grounding
  T4 = 0.4  git precedent
  T5 = 0.1  LLM assertion with no backing
"""
from __future__ import annotations

import logging
from collections import defaultdict

from patchcourt.agents.schemas import Claim, Evidence
from patchcourt.tools import Finding, run_enabled_tools

logger = logging.getLogger("patchcourt.evidence")


def tier_for_findings(findings: list[Finding]) -> tuple[int, bool]:
    """T1 for a single tool flag; T2 when two or more tools agree on the line."""
    tools = {f.tool for f in findings}
    if len(tools) >= 2:
        return 2, True
    return 1, False


def normalize_findings(
    findings: list[Finding],
    rag_files: set[str] | None = None,
    git_precedent: dict | None = None,
) -> list[Claim]:
    """Group findings by (file, line) and emit one tiered Claim per location."""
    rag_files = rag_files or set()
    groups: dict[tuple[str, int], list[Finding]] = defaultdict(list)
    for f in findings:
        if f.line >= 1:
            groups[(f.file, f.line)].append(f)

    claims: list[Claim] = []
    for (file, line), fs in groups.items():
        tier, corroborated = tier_for_findings(fs)
        best = max(fs, key=lambda f: f.severity)
        evidence = [
            Evidence(tier=1, text=f"[{f.tool}] {f.message}")
            for f in sorted(fs, key=lambda x: x.tool)
        ]
        if file in rag_files:
            evidence.append(Evidence(tier=3, text="file surfaced by repo-context RAG grounding"))
            if tier > 3:
                tier = 3 if not corroborated else tier
        claims.append(
            Claim(
                agent="tools",
                issue=f"[{best.rule}] {best.message}" if best.rule else best.message,
                file=file,
                line=line,
                severity=best.severity,
                evidence=evidence,
                confidence=1.0,
                tier=tier,
                corroborated=corroborated,
                source="tool",
            )
        )
    return claims


class EvidenceEngine:
    """Runs the enabled tools and normalizes results into claims."""

    def __init__(self, runner=run_enabled_tools) -> None:
        self._runner = runner

    async def analyze(
        self,
        file_contents: dict[str, str],
        rag_results: list[dict] | None = None,
        git_precedent: dict | None = None,
    ) -> list[Claim]:
        rag_files = {r.get("metadata", {}).get("file", "") for r in (rag_results or [])}
        findings = await self._runner(file_contents)
        if not findings:
            return []
        return normalize_findings(findings, rag_files=rag_files, git_precedent=git_precedent)


def _finding_tier_total(tool_claims: list[Claim]) -> dict[tuple[str, int], int]:
    index: dict[tuple[str, int], int] = {}
    for c in tool_claims:
        index[(c.file, c.line)] = c.tier
    return index


def corroborate_claims(tool_claims: list[Claim], llm_claims: list[Claim]) -> list[Claim]:
    """An LLM claim matching a tool finding on file+line gets upgraded to the
    tool tier and marked corroborated."""
    index = _finding_tier_total(tool_claims)
    out = list(tool_claims)
    for c in llm_claims:
        matching_tier = index.get((c.file, c.line))
        if matching_tier is not None and not c.source.startswith("tool"):
            upgraded = min(c.tier, matching_tier)
            c.tier = upgraded
            c.corroborated = True
            c.evidence = [
                *c.evidence,
                Evidence(tier=upgraded, text=f"corroborated by static-analysis tool on {c.file}:{c.line}"),
            ]
        out.append(c)
    return out