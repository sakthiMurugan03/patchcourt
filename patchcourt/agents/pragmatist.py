"""Pragmatist agent — cost/benefit and risk-of-blocking review."""
from __future__ import annotations

from patchcourt.agents.base import BaseAgent


class PragmatistAgent(BaseAgent):
    name = "pragmatist"

    def system_prompt(self) -> str:
        return (
            "You are the pragmatic reviewer representing the engineering team's velocity. "
            "Flag only things worth stopping a merge for; assess blast radius, test coverage, "
            "and whether a fix is trivial or invasive. Push back on over-blocking. "
            "Respond ONLY as JSON: "
            '{"claims":[{"issue":"...","file":"...","line":1,"severity":1..5,'
            '"evidence":[{"tier":1..5,"text":"..."}],"confidence":0..1,"tier":1..5}]}\n'
            "Tier rules: T1 = blocker with provable impact, T2 = directly observed regression risk, "
            "T3 = reasonable diff-based concern, T4 = weak signal, T5 = pure preference."
        )

    def build_user_prompt(self, pr, rag_results, tool_findings=None):
        return (
            "Review this PR from a PRAGMATIST perspective (cost/benefit, merge risk).\n\n"
            + super().build_user_prompt(pr, rag_results, tool_findings)
        )